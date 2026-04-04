"""Tests for the compact module."""

from __future__ import annotations

import textwrap
from datetime import date
from pathlib import Path

import pytest

from anamnesis.compact import (
    CompactResult,
    DuplicateGroup,
    compact_report,
    find_duplicates,
    _scan_memories,
)


def _make_memory(dir_path: Path, name: str, title: str, content: str, **fm_extra) -> Path:
    """Write a memory file with frontmatter."""
    import yaml

    fm = {
        "type": "knowledge",
        "tags": [],
        "created": "2026-01-01",
        "last_accessed": "2026-04-01",
        "access_count": 1,
        "importance": "medium",
    }
    fm.update(fm_extra)

    path = dir_path / f"{name}.md"
    frontmatter = yaml.dump(fm, default_flow_style=False).strip()
    path.write_text(f"---\n{frontmatter}\n---\n\n# {title}\n\n{content}\n")
    return path


@pytest.fixture
def memory_dir(tmp_path):
    d = tmp_path / "memory"
    for sub in ("knowledge", "tasks", "contexts", "reflections"):
        (d / sub).mkdir(parents=True)
    return d


class TestScanMemories:
    def test_finds_files(self, memory_dir):
        _make_memory(memory_dir / "knowledge", "auth", "Auth", "JWT tokens")
        _make_memory(memory_dir / "tasks", "deploy", "Deploy", "Step 1")
        files = _scan_memories(memory_dir)
        assert len(files) == 2

    def test_skips_readme(self, memory_dir):
        (memory_dir / "knowledge" / "README.md").write_text("# Readme\n")
        _make_memory(memory_dir / "knowledge", "auth", "Auth", "JWT tokens")
        files = _scan_memories(memory_dir)
        assert len(files) == 1

    def test_empty_dir(self, memory_dir):
        assert _scan_memories(memory_dir) == []


class TestFindDuplicates:
    def test_exact_duplicates(self, memory_dir):
        _make_memory(memory_dir / "knowledge", "auth-1", "API Authentication", "Use JWT tokens for auth")
        _make_memory(memory_dir / "knowledge", "auth-2", "API Authentication", "Use JWT tokens for auth")
        groups = find_duplicates(memory_dir)
        assert len(groups) == 1
        assert len(groups[0].files) == 2

    def test_no_duplicates(self, memory_dir):
        _make_memory(memory_dir / "knowledge", "auth", "API Auth", "JWT tokens for authentication")
        _make_memory(memory_dir / "knowledge", "docker", "Docker Setup", "Use docker compose for local dev")
        groups = find_duplicates(memory_dir)
        assert len(groups) == 0

    def test_near_duplicates(self, memory_dir):
        _make_memory(memory_dir / "knowledge", "auth-1", "API Authentication Guide",
                     "Use JWT tokens for API authentication and authorization")
        _make_memory(memory_dir / "knowledge", "auth-2", "API Authentication",
                     "JWT tokens are used for API authentication")
        groups = find_duplicates(memory_dir, threshold=0.5)
        assert len(groups) == 1

    def test_single_file(self, memory_dir):
        _make_memory(memory_dir / "knowledge", "auth", "Auth", "tokens")
        assert find_duplicates(memory_dir) == []


class TestCompactReport:
    def test_empty_dir(self, memory_dir):
        result = compact_report(memory_dir)
        assert result.total_memories == 0
        assert result.duplicates == []

    def test_with_stale_and_dupes(self, memory_dir):
        _make_memory(memory_dir / "knowledge", "auth-1", "Auth", "JWT tokens",
                     last_accessed=date(2025, 1, 1))
        _make_memory(memory_dir / "knowledge", "auth-2", "Auth", "JWT tokens",
                     last_accessed=date(2026, 4, 1))
        result = compact_report(
            memory_dir,
            decay_threshold_days=90,
            today=date(2026, 4, 4),
        )
        assert result.total_memories == 2
        # One stale memory
        assert len(result.decay.stale) >= 1
        # One duplicate group
        assert len(result.duplicates) == 1
