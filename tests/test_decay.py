"""Tests for the decay module."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from anamnesis.decay import (
    _extract_title,
    _parse_frontmatter,
    archive_memory,
    decay_report,
    find_stale_memories,
    run_decay,
)

TODAY = date(2026, 4, 4)


def _make_memory(directory: Path, name: str, last_accessed: str, importance: str = "medium", mem_type: str = "knowledge") -> Path:
    """Helper to create a memory file with frontmatter."""
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ntype: {mem_type}\nlast_accessed: {last_accessed}\nimportance: {importance}\n---\n\n# {path.stem}\nContent.\n"
    )
    return path


def _setup_memory_dir(tmp_path: Path) -> Path:
    mem = tmp_path / "memory"
    for d in ("knowledge", "tasks", "contexts", "reflections", "archive"):
        (mem / d).mkdir(parents=True)
    return mem


class TestFindStaleMemories:
    def test_finds_stale(self, tmp_path: Path) -> None:
        mem = _setup_memory_dir(tmp_path)
        _make_memory(mem / "knowledge", "old.md", "2025-12-01")
        result = find_stale_memories(mem, threshold_days=90, today=TODAY)
        assert len(result) == 1
        assert result[0].path == mem / "knowledge" / "old.md"
        assert result[0].days_stale == (TODAY - date(2025, 12, 1)).days

    def test_none_stale(self, tmp_path: Path) -> None:
        mem = _setup_memory_dir(tmp_path)
        _make_memory(mem / "knowledge", "fresh.md", "2026-03-30")
        result = find_stale_memories(mem, threshold_days=90, today=TODAY)
        assert result == []

    def test_mixed(self, tmp_path: Path) -> None:
        mem = _setup_memory_dir(tmp_path)
        _make_memory(mem / "knowledge", "old.md", "2025-11-01")
        _make_memory(mem / "tasks", "recent.md", "2026-03-30")
        _make_memory(mem / "reflections", "ancient.md", "2025-01-01")
        result = find_stale_memories(mem, threshold_days=90, today=TODAY)
        assert len(result) == 2
        # Most stale first
        assert result[0].path.name == "ancient.md"
        assert result[1].path.name == "old.md"


class TestArchiveMemory:
    def test_archive(self, tmp_path: Path) -> None:
        mem = _setup_memory_dir(tmp_path)
        src = _make_memory(mem / "knowledge", "topic.md", "2025-12-01")
        archive_dir = mem / "archive"
        new_path = archive_memory(src, archive_dir, today=TODAY)
        assert new_path == archive_dir / "2026-04" / "topic.md"
        assert new_path.exists()
        assert not src.exists()

    def test_name_collision(self, tmp_path: Path) -> None:
        mem = _setup_memory_dir(tmp_path)
        archive_dir = mem / "archive"
        month_dir = archive_dir / "2026-04"
        month_dir.mkdir(parents=True)
        (month_dir / "topic.md").write_text("existing")

        src = _make_memory(mem / "knowledge", "topic.md", "2025-12-01")
        new_path = archive_memory(src, archive_dir, today=TODAY)
        assert new_path == month_dir / "topic-2.md"
        assert new_path.exists()
        assert not src.exists()


class TestDecayReport:
    def test_report_without_archiving(self, tmp_path: Path) -> None:
        mem = _setup_memory_dir(tmp_path)
        src = _make_memory(mem / "knowledge", "old.md", "2025-12-01")
        result = decay_report(mem, threshold_days=90, today=TODAY)
        assert len(result.stale) == 1
        assert result.archived == []
        assert result.kept == []
        assert src.exists()


class TestRunDecay:
    def test_full_flow(self, tmp_path: Path) -> None:
        mem = _setup_memory_dir(tmp_path)
        _make_memory(mem / "knowledge", "old.md", "2025-12-01")
        _make_memory(mem / "tasks", "fresh.md", "2026-03-30")
        result = run_decay(mem, threshold_days=90, today=TODAY)
        assert len(result.archived) == 1
        assert len(result.stale) == 1
        assert not (mem / "knowledge" / "old.md").exists()

    def test_protects_high_importance(self, tmp_path: Path) -> None:
        mem = _setup_memory_dir(tmp_path)
        _make_memory(mem / "knowledge", "critical.md", "2025-12-01", importance="high")
        _make_memory(mem / "tasks", "low.md", "2025-12-01", importance="low")
        result = run_decay(mem, threshold_days=90, protect_high_importance=True, today=TODAY)
        assert len(result.kept) == 1
        assert result.kept[0].name == "critical.md"
        assert len(result.archived) == 1
        assert (mem / "knowledge" / "critical.md").exists()
        assert not (mem / "tasks" / "low.md").exists()


class TestParseFrontmatter:
    def test_valid_yaml(self, tmp_path: Path) -> None:
        p = tmp_path / "test.md"
        p.write_text("---\ntype: knowledge\ntags: [a, b]\n---\n# Title\n")
        fm = _parse_frontmatter(p)
        assert fm["type"] == "knowledge"
        assert fm["tags"] == ["a", "b"]

    def test_no_yaml(self, tmp_path: Path) -> None:
        p = tmp_path / "test.md"
        p.write_text("# Just a heading\nNo frontmatter here.\n")
        assert _parse_frontmatter(p) == {}


class TestSkipsArchiveDir:
    def test_skips_archive(self, tmp_path: Path) -> None:
        mem = _setup_memory_dir(tmp_path)
        # Put a stale file in archive/ — it should NOT be scanned
        _make_memory(mem / "archive", "archived.md", "2025-01-01")
        result = find_stale_memories(mem, threshold_days=90, today=TODAY)
        assert result == []
