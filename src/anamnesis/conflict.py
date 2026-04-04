"""Conflict detection and resolution for memory files."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path

import yaml


class Strategy(Enum):
    MERGE = "merge"
    REPLACE = "replace"
    SKIP = "skip"
    ASK = "ask"


STOP_WORDS = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would shall should may might can could of in to for on with "
    "at by from as into about between through and or but not no nor".split()
)


@dataclass
class MemoryFile:
    """Parsed memory file with frontmatter and content."""

    path: Path
    memory_type: str
    tags: list[str]
    title: str
    content: str
    created: str = ""
    last_accessed: str = ""
    access_count: int = 0
    importance: str = "medium"


@dataclass
class ConflictResult:
    """A detected conflict between new and existing memory."""

    existing: MemoryFile
    similarity: float
    overlap_type: str
    suggested_strategy: Strategy


def parse_memory_file(path: Path) -> MemoryFile:
    """Parse a memory markdown file with YAML frontmatter."""
    text = path.read_text(encoding="utf-8")

    meta: dict = {}
    content = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            meta = yaml.safe_load(parts[1]) or {}
            content = parts[2].strip()

    # Extract title from first markdown heading
    title = ""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            break

    return MemoryFile(
        path=path,
        memory_type=meta.get("type", ""),
        tags=meta.get("tags", []),
        title=title,
        content=content,
        created=str(meta.get("created", "")),
        last_accessed=str(meta.get("last_accessed", "")),
        access_count=int(meta.get("access_count", 0)),
        importance=meta.get("importance", "medium"),
    )


def _tokenize(text: str) -> set[str]:
    """Lowercase and split into words, removing stop words."""
    words = set(text.lower().split())
    return words - STOP_WORDS


def compute_title_similarity(a: str, b: str) -> float:
    """Simple word-overlap (Jaccard) similarity between two titles."""
    words_a = _tokenize(a)
    words_b = _tokenize(b)
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def compute_content_similarity(a: str, b: str) -> float:
    """Jaccard similarity of significant words (stop words removed)."""
    words_a = _tokenize(a)
    words_b = _tokenize(b)
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _compute_tag_overlap(tags_a: list[str], tags_b: list[str]) -> float:
    """Fraction of shared tags relative to the smaller set."""
    if not tags_a or not tags_b:
        return 0.0
    set_a = set(tags_a)
    set_b = set(tags_b)
    shared = set_a & set_b
    return len(shared) / min(len(set_a), len(set_b))


def _combined_score(title_sim: float, content_sim: float, tag_sim: float) -> float:
    return 0.4 * title_sim + 0.4 * content_sim + 0.2 * tag_sim


def _overlap_type(title_sim: float, content_sim: float, tag_sim: float) -> str:
    scores = {"title": title_sim, "content": content_sim, "tags": tag_sim}
    dominant = max(scores, key=scores.get)  # type: ignore[arg-type]
    if title_sim > 0.3 and content_sim > 0.3:
        return "combined"
    return dominant


def suggest_strategy(conflict: ConflictResult) -> Strategy:
    """Suggest a resolution strategy based on similarity and overlap type."""
    if conflict.similarity > 0.8:
        return Strategy.SKIP
    if conflict.similarity > 0.6:
        return Strategy.MERGE
    if conflict.similarity > 0.4:
        return Strategy.ASK
    return Strategy.SKIP  # below threshold — shouldn't normally be called


def find_conflicts(
    title: str,
    content: str,
    tags: list[str],
    memory_type: str,
    memory_dir: Path,
) -> list[ConflictResult]:
    """Find existing memories that conflict with a proposed new memory."""
    if not memory_dir.exists():
        return []

    results: list[ConflictResult] = []
    for md_file in memory_dir.rglob("*.md"):
        if md_file.name in ("MEMORY.md", "INDEX.md", "README.md"):
            continue

        existing = parse_memory_file(md_file)

        title_sim = compute_title_similarity(title, existing.title)
        content_sim = compute_content_similarity(content, existing.content)
        tag_sim = _compute_tag_overlap(tags, existing.tags)
        combined = _combined_score(title_sim, content_sim, tag_sim)

        if combined < 0.4:
            continue

        otype = _overlap_type(title_sim, content_sim, tag_sim)
        conflict = ConflictResult(
            existing=existing,
            similarity=combined,
            overlap_type=otype,
            suggested_strategy=Strategy.ASK,  # placeholder
        )
        conflict.suggested_strategy = suggest_strategy(conflict)
        results.append(conflict)

    results.sort(key=lambda c: c.similarity, reverse=True)
    return results


def merge_memories(existing: MemoryFile, new_content: str, new_tags: list[str]) -> str:
    """Merge new content into an existing memory file. Returns merged markdown."""
    text = existing.path.read_text(encoding="utf-8")

    # Update tags in frontmatter
    merged_tags = sorted(set(existing.tags) | set(new_tags))
    today = date.today().isoformat()

    meta: dict = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            meta = yaml.safe_load(parts[1]) or {}
            body = parts[2]

    meta["tags"] = merged_tags
    meta["last_accessed"] = today

    frontmatter = yaml.dump(meta, default_flow_style=False).strip()
    body = body.rstrip() + f"\n\n## Updated {today}\n{new_content.strip()}\n"

    return f"---\n{frontmatter}\n---\n{body}"
