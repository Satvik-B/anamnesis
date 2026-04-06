"""Extraction heuristics for identifying memory candidates in conversation text.

Uses regex/keyword pattern matching to classify text passages into memory types
(gotcha, knowledge, task, reflection) without any LLM dependency.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class MemoryType(Enum):
    GOTCHA = "gotcha"
    KNOWLEDGE = "knowledge"
    TASK = "task"
    REFLECTION = "reflection"


@dataclass
class ExtractedMemory:
    memory_type: MemoryType
    title: str
    content: str
    confidence: float
    tags: list[str] = field(default_factory=list)
    source_line: int = 0


# ---------------------------------------------------------------------------
# Signal-phrase patterns per memory type
# ---------------------------------------------------------------------------
# Each entry is (compiled_regex, is_strong).  "Strong" patterns are ones that
# include a colon or are very specific indicators — they get higher confidence.

_PATTERNS: dict[MemoryType, list[tuple[re.Pattern[str], bool]]] = {
    MemoryType.GOTCHA: [
        (re.compile(r"\bgotcha\b", re.IGNORECASE), False),
        (re.compile(r"\bwatch\s+out\b", re.IGNORECASE), False),
        (re.compile(r"\bcareful\s+with\b", re.IGNORECASE), False),
        (re.compile(r"\bdon'?t\s+forget\b", re.IGNORECASE), False),
        (re.compile(r"\bheads\s+up\b", re.IGNORECASE), False),
        (re.compile(r"\bcaveat\b", re.IGNORECASE), False),
        (re.compile(r"\btrap\b", re.IGNORECASE), False),
        (re.compile(r"\bpitfall\b", re.IGNORECASE), False),
        (re.compile(r"\bbeware\b", re.IGNORECASE), False),
        (re.compile(r"\bworkaround\b", re.IGNORECASE), False),
        # Strong (with colon or very explicit)
        (re.compile(r"\bgotcha\s*:", re.IGNORECASE), True),
        (re.compile(r"\bimportant\s*:", re.IGNORECASE), True),
        (re.compile(r"\bwarning\s*:", re.IGNORECASE), True),
        (re.compile(r"\bnote\s*:", re.IGNORECASE), True),
        (re.compile(r"\bbug\s*:", re.IGNORECASE), True),
        (re.compile(r"\bworkaround\s*:", re.IGNORECASE), True),
    ],
    MemoryType.KNOWLEDGE: [
        (re.compile(r"\bTIL\b"), False),
        (re.compile(r"\blearned\s+that\b", re.IGNORECASE), False),
        (re.compile(r"\bturns\s+out\b", re.IGNORECASE), False),
        (re.compile(r"\bthe\s+trick\s+is\b", re.IGNORECASE), False),
        (re.compile(r"\bconvention\s+is\b", re.IGNORECASE), False),
        (re.compile(r"\bpattern\s+is\b", re.IGNORECASE), False),
        (re.compile(r"\bworks\s+by\b", re.IGNORECASE), False),
        (re.compile(r"\bthe\s+reason\b", re.IGNORECASE), False),
        (re.compile(r"\barchitecture\b", re.IGNORECASE), False),
        (re.compile(r"\bdesign\s+decision\b", re.IGNORECASE), False),
        # Strong
        (re.compile(r"\bTIL\s*:"), True),
    ],
    MemoryType.TASK: [
        (re.compile(r"\bsteps\s*:", re.IGNORECASE), True),
        (re.compile(r"\bto\s+do\s+this\s*:", re.IGNORECASE), True),
        (re.compile(r"\bprocedure\s*:", re.IGNORECASE), True),
        (re.compile(r"\bhow\s+to\b", re.IGNORECASE), False),
        (re.compile(r"\bfirst\s*,", re.IGNORECASE), False),
        (re.compile(r"\bthen\s*,", re.IGNORECASE), False),
        (re.compile(r"\bfinally\s*,", re.IGNORECASE), False),
        # Numbered list: lines starting with "1." or "1)"
        (re.compile(r"^\s*1[.)]\s", re.MULTILINE), False),
    ],
    MemoryType.REFLECTION: [
        (re.compile(r"\bmistake\b", re.IGNORECASE), False),
        (re.compile(r"\bshould\s+have\b", re.IGNORECASE), False),
        (re.compile(r"\bnext\s+time\b", re.IGNORECASE), False),
        (re.compile(r"\blesson\b", re.IGNORECASE), False),
        (re.compile(r"\bin\s+hindsight\b", re.IGNORECASE), False),
        (re.compile(r"\bwrong\s+approach\b", re.IGNORECASE), False),
        (re.compile(r"\bbetter\s+approach\b", re.IGNORECASE), False),
        (re.compile(r"\bwhat\s+went\s+wrong\b", re.IGNORECASE), False),
        (re.compile(r"\bfix\s+was\b", re.IGNORECASE), False),
        # Strong
        (re.compile(r"\blesson\s*:", re.IGNORECASE), True),
        (re.compile(r"\bmistake\s*:", re.IGNORECASE), True),
    ],
}

# Technical terms used for tag inference
_TAG_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bAPI\b"), "api"),
    (re.compile(r"\bdatabase\b", re.IGNORECASE), "database"),
    (re.compile(r"\bSQL\b"), "sql"),
    (re.compile(r"\bDocker\b", re.IGNORECASE), "docker"),
    (re.compile(r"\bCI\b"), "ci"),
    (re.compile(r"\bCD\b"), "cd"),
    (re.compile(r"\bCI/CD\b", re.IGNORECASE), "ci-cd"),
    (re.compile(r"\bgit\b", re.IGNORECASE), "git"),
    (re.compile(r"\bpython\b", re.IGNORECASE), "python"),
    (re.compile(r"\brust\b", re.IGNORECASE), "rust"),
    (re.compile(r"\btypescript\b", re.IGNORECASE), "typescript"),
    (re.compile(r"\bjavascript\b", re.IGNORECASE), "javascript"),
    (re.compile(r"\breact\b", re.IGNORECASE), "react"),
    (re.compile(r"\bkubernetes\b", re.IGNORECASE), "kubernetes"),
    (re.compile(r"\bk8s\b", re.IGNORECASE), "kubernetes"),
    (re.compile(r"\bauth\b", re.IGNORECASE), "auth"),
    (re.compile(r"\bcaching?\b", re.IGNORECASE), "caching"),
    (re.compile(r"\btesting?\b", re.IGNORECASE), "testing"),
    (re.compile(r"\bperformance\b", re.IGNORECASE), "performance"),
    (re.compile(r"\bsecurity\b", re.IGNORECASE), "security"),
    (re.compile(r"\bmigration\b", re.IGNORECASE), "migration"),
    (re.compile(r"\bdeployment\b", re.IGNORECASE), "deployment"),
    (re.compile(r"\bconfiguration\b", re.IGNORECASE), "configuration"),
    (re.compile(r"\bregex\b", re.IGNORECASE), "regex"),
]


def extract_memories(text: str) -> list[ExtractedMemory]:
    """Scan text for memory candidates using pattern heuristics.

    Returns extracted memories sorted by confidence (highest first).
    Deduplicates overlapping extractions.
    """
    lines = text.splitlines()
    candidates: list[ExtractedMemory] = []

    for line_idx, line in enumerate(lines):
        for memory_type, patterns in _PATTERNS.items():
            weak_hits = 0
            strong_hits = 0

            for pattern, is_strong in patterns:
                if pattern.search(line):
                    if is_strong:
                        strong_hits += 1
                    else:
                        weak_hits += 1

            if weak_hits == 0 and strong_hits == 0:
                continue

            context = _extract_context(lines, line_idx, context_lines=3)

            # Also count signals in the surrounding context for confidence
            context_weak = 0
            context_strong = 0
            context_start = max(0, line_idx - 3)
            context_end = min(len(lines), line_idx + 4)
            for ctx_idx in range(context_start, context_end):
                if ctx_idx == line_idx:
                    continue
                for pattern, is_strong in patterns:
                    if pattern.search(lines[ctx_idx]):
                        if is_strong:
                            context_strong += 1
                        else:
                            context_weak += 1

            total_weak = weak_hits + context_weak
            total_strong = strong_hits + context_strong

            confidence = _compute_confidence(
                total_weak, total_strong, len(context.strip())
            )

            title = _generate_title(context, memory_type)
            tags = _infer_tags(context)

            candidates.append(
                ExtractedMemory(
                    memory_type=memory_type,
                    title=title,
                    content=context,
                    confidence=confidence,
                    tags=tags,
                    source_line=line_idx,
                )
            )

    deduped = _deduplicate(candidates)
    deduped.sort(key=lambda m: m.confidence, reverse=True)
    return deduped


def _extract_context(
    lines: list[str], match_line: int, context_lines: int = 3
) -> str:
    """Extract surrounding context around a match."""
    start = max(0, match_line - context_lines)
    end = min(len(lines), match_line + context_lines + 1)
    return "\n".join(lines[start:end])


def _generate_title(content: str, memory_type: MemoryType) -> str:
    """Generate a short title from the content.

    Takes the first non-empty, meaningful line and truncates it.
    """
    max_title_len = 80

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Skip lines that are just numbering or bullets
        cleaned = re.sub(r"^\s*[\d]+[.)]\s*", "", stripped)
        cleaned = re.sub(r"^\s*[-*]\s*", "", cleaned)
        if not cleaned:
            continue
        # Remove trailing punctuation for cleaner title
        cleaned = cleaned.rstrip(":.;,")
        if len(cleaned) > max_title_len:
            cleaned = cleaned[:max_title_len].rsplit(" ", 1)[0] + "..."
        return cleaned

    return f"{memory_type.value} memory"


def _infer_tags(content: str) -> list[str]:
    """Infer tags from content keywords."""
    tags: list[str] = []
    seen: set[str] = set()
    for pattern, tag in _TAG_PATTERNS:
        if tag not in seen and pattern.search(content):
            tags.append(tag)
            seen.add(tag)
    return tags


def _compute_confidence(
    weak_count: int, strong_count: int, content_length: int
) -> float:
    """Compute a confidence score from signal counts and content length.

    Scoring rules:
    - Single weak signal phrase match: 0.4
    - Multiple signal phrases in context: 0.6
    - Strong signal phrase (with colon): 0.8
    - Multiple strong signals: 0.9
    - Very short content (< 20 chars) gets a penalty
    """
    if strong_count >= 2:
        confidence = 0.9
    elif strong_count >= 1:
        confidence = 0.8
    elif weak_count >= 2:
        confidence = 0.6
    else:
        confidence = 0.4

    # Penalize very short content
    if content_length < 20:
        confidence *= 0.5

    return min(confidence, 1.0)


def _deduplicate(candidates: list[ExtractedMemory]) -> list[ExtractedMemory]:
    """Remove overlapping extractions, keeping the higher-confidence one.

    Two extractions overlap if they are of the same type and their source
    lines are within 2 lines of each other.
    """
    if not candidates:
        return []

    # Sort by type then source_line for grouping
    candidates.sort(key=lambda m: (m.memory_type.value, m.source_line))

    kept: list[ExtractedMemory] = []
    for candidate in candidates:
        merged = False
        for i, existing in enumerate(kept):
            if (
                existing.memory_type == candidate.memory_type
                and abs(existing.source_line - candidate.source_line) <= 2
            ):
                # Keep the higher-confidence one
                if candidate.confidence > existing.confidence:
                    kept[i] = candidate
                merged = True
                break
        if not merged:
            kept.append(candidate)

    return kept
