"""Detect and archive stale memories based on last_accessed frontmatter."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

DEFAULT_THRESHOLD_DAYS = 90

SCAN_DIRS = ("knowledge", "tasks", "contexts", "reflections")


@dataclass
class StaleMemory:
    path: Path
    title: str
    memory_type: str
    last_accessed: date
    days_stale: int
    importance: str


@dataclass
class DecayResult:
    stale: list[StaleMemory] = field(default_factory=list)
    archived: list[Path] = field(default_factory=list)
    kept: list[Path] = field(default_factory=list)


def _parse_frontmatter(path: Path) -> dict:
    """Parse YAML frontmatter from a markdown file. Returns empty dict on failure."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        return {}


def _extract_title(path: Path) -> str:
    """Extract the first # heading from a markdown file."""
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    except OSError:
        pass
    return path.stem


def find_stale_memories(
    memory_dir: Path,
    threshold_days: int = DEFAULT_THRESHOLD_DAYS,
    today: date | None = None,
) -> list[StaleMemory]:
    """Scan memory subdirectories for files with last_accessed older than threshold."""
    today = today or date.today()
    stale: list[StaleMemory] = []

    for subdir_name in SCAN_DIRS:
        subdir = memory_dir / subdir_name
        if not subdir.is_dir():
            continue
        for md_file in subdir.glob("*.md"):
            fm = _parse_frontmatter(md_file)
            la = fm.get("last_accessed")
            if isinstance(la, str):
                try:
                    la = date.fromisoformat(la)
                except ValueError:
                    continue
            if not isinstance(la, date):
                continue
            days = (today - la).days
            if days >= threshold_days:
                stale.append(StaleMemory(
                    path=md_file,
                    title=_extract_title(md_file),
                    memory_type=fm.get("type", "unknown"),
                    last_accessed=la,
                    days_stale=days,
                    importance=fm.get("importance", "medium"),
                ))

    stale.sort(key=lambda s: s.days_stale, reverse=True)
    return stale


def archive_memory(
    memory_path: Path,
    archive_dir: Path,
    today: date | None = None,
) -> Path:
    """Move a memory file to archive/YYYY-MM/ directory."""
    today = today or date.today()
    month_dir = archive_dir / today.strftime("%Y-%m")
    month_dir.mkdir(parents=True, exist_ok=True)

    dest = month_dir / memory_path.name
    if dest.exists():
        stem = memory_path.stem
        suffix = memory_path.suffix
        counter = 2
        while dest.exists():
            dest = month_dir / f"{stem}-{counter}{suffix}"
            counter += 1

    shutil.move(str(memory_path), str(dest))
    return dest


def decay_report(
    memory_dir: Path,
    threshold_days: int = DEFAULT_THRESHOLD_DAYS,
    today: date | None = None,
) -> DecayResult:
    """Generate a report of stale memories without archiving them."""
    stale = find_stale_memories(memory_dir, threshold_days, today)
    return DecayResult(stale=stale)


def run_decay(
    memory_dir: Path,
    threshold_days: int = DEFAULT_THRESHOLD_DAYS,
    protect_high_importance: bool = True,
    today: date | None = None,
) -> DecayResult:
    """Find and archive stale memories."""
    today = today or date.today()
    stale = find_stale_memories(memory_dir, threshold_days, today)
    archive_dir = memory_dir / "archive"
    result = DecayResult(stale=stale)

    for mem in stale:
        if protect_high_importance and mem.importance == "high":
            result.kept.append(mem.path)
        else:
            new_path = archive_memory(mem.path, archive_dir, today)
            result.archived.append(new_path)

    return result
