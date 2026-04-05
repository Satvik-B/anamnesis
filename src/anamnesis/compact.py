"""Compact — find duplicate memories and run decay on stale ones.

Provides structural analysis for the CLI (`anamnesis compact`) and the
Claude Code skill (`/memory compact`).  Claude handles semantic merging;
this module handles scanning, scoring, and archiving.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from anamnesis.conflict import (
    MemoryFile,
    parse_memory_file,
    compute_title_similarity,
    compute_content_similarity,
)
from anamnesis.decay import (
    DEFAULT_THRESHOLD_DAYS,
    DecayResult,
    decay_report as _decay_report,
    find_stale_memories,
    run_decay,
)


@dataclass
class DuplicateGroup:
    """A set of memory files that appear to be duplicates or near-duplicates."""

    files: list[MemoryFile]
    similarity: float


@dataclass
class CompactResult:
    """Summary of a compact operation."""

    duplicates: list[DuplicateGroup] = field(default_factory=list)
    decay: DecayResult | None = None
    total_memories: int = 0


SCAN_DIRS = ("knowledge", "tasks", "contexts", "reflections")


def _scan_memories(memory_dir: Path) -> list[MemoryFile]:
    """Load all memory files from standard subdirectories."""
    files: list[MemoryFile] = []
    for subdir_name in SCAN_DIRS:
        subdir = memory_dir / subdir_name
        if not subdir.is_dir():
            continue
        for md in subdir.glob("*.md"):
            if md.name in ("README.md",):
                continue
            files.append(parse_memory_file(md))
    return files


def find_duplicates(
    memory_dir: Path,
    threshold: float = 0.6,
) -> list[DuplicateGroup]:
    """Identify groups of memories that are likely duplicates.

    Two memories are grouped if their combined title + content similarity
    exceeds *threshold*.
    """
    files = _scan_memories(memory_dir)
    if len(files) < 2:
        return []

    # Track which files have already been grouped
    grouped: set[str] = set()
    groups: list[DuplicateGroup] = []

    for i, a in enumerate(files):
        if str(a.path) in grouped:
            continue
        group_members = [a]
        best_sim = 0.0

        for j in range(i + 1, len(files)):
            b = files[j]
            if str(b.path) in grouped:
                continue

            title_sim = compute_title_similarity(a.title, b.title)
            content_sim = compute_content_similarity(a.content, b.content)
            combined = 0.5 * title_sim + 0.5 * content_sim

            if combined >= threshold:
                group_members.append(b)
                grouped.add(str(b.path))
                best_sim = max(best_sim, combined)

        if len(group_members) > 1:
            grouped.add(str(a.path))
            groups.append(DuplicateGroup(files=group_members, similarity=best_sim))

    groups.sort(key=lambda g: g.similarity, reverse=True)
    return groups


def compact_report(
    memory_dir: Path,
    decay_threshold_days: int = DEFAULT_THRESHOLD_DAYS,
    duplicate_threshold: float = 0.6,
    today: date | None = None,
) -> CompactResult:
    """Generate a compact report: duplicates + stale memories.

    Does not modify any files — purely diagnostic.
    """
    files = _scan_memories(memory_dir)
    duplicates = find_duplicates(memory_dir, duplicate_threshold)
    decay = _decay_report(memory_dir, decay_threshold_days, today=today)

    return CompactResult(
        duplicates=duplicates,
        decay=decay,
        total_memories=len(files),
    )
