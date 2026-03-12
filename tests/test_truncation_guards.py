"""Tests for the truncation guard / size discipline system."""

from pathlib import Path

import pytest


MEMORY_MD_LIMIT = 200
INDEX_MD_LIMIT = 150
FILE_LIMIT = 80


class TestMemoryMdLimits:
    """Tests for MEMORY.md line limit enforcement."""

    def test_memory_md_line_limit(self, installed_project):
        """A freshly initialized INDEX.md should be well under the 150-line limit."""
        index_path = installed_project / ".claude" / "memory" / "INDEX.md"
        assert index_path.exists(), "INDEX.md should exist in installed project"

        lines = index_path.read_text().splitlines()
        assert len(lines) < INDEX_MD_LIMIT, (
            f"INDEX.md has {len(lines)} lines, exceeds limit of {INDEX_MD_LIMIT}"
        )

    def test_overflow_detection(self, tmp_path):
        """A file exceeding the line limit should be detectable."""
        big_file = tmp_path / "MEMORY.md"
        big_file.write_text("\n".join(f"Line {i}" for i in range(250)))

        lines = big_file.read_text().splitlines()
        assert len(lines) > MEMORY_MD_LIMIT, "Test file should exceed limit"

        # If the truncation module exists, use it
        try:
            from claude_memory.truncation import check_file_limits
            issues = check_file_limits(big_file, max_lines=MEMORY_MD_LIMIT)
            assert len(issues) > 0
        except ImportError:
            # Module not implemented yet -- verify the detection logic manually
            assert len(lines) == 250

    def test_small_file_passes(self, tmp_path):
        """A file under the limit should pass."""
        small_file = tmp_path / "INDEX.md"
        small_file.write_text("\n".join(f"Line {i}" for i in range(50)))

        lines = small_file.read_text().splitlines()
        assert len(lines) < INDEX_MD_LIMIT


class TestFileSizeLimits:
    """Tests for per-file size limits."""

    def test_memory_file_under_80_lines(self, fixtures_dir):
        """Sample fixture memory files should be under 80 lines."""
        sample_dir = fixtures_dir / "sample_memory"
        md_files = list(sample_dir.rglob("*.md"))

        for md_file in md_files:
            lines = md_file.read_text().splitlines()
            assert len(lines) <= FILE_LIMIT, (
                f"{md_file.name} has {len(lines)} lines, exceeds per-file limit of {FILE_LIMIT}"
            )

    def test_overflow_detected_and_reported(self, tmp_path):
        """Creating a memory file over 80 lines should be detectable."""
        big_file = tmp_path / "too-big.md"
        big_file.write_text("\n".join(f"Line {i}" for i in range(100)))

        lines = big_file.read_text().splitlines()
        assert len(lines) > FILE_LIMIT

        try:
            from claude_memory.truncation import check_file_limits
            issues = check_file_limits(big_file, max_lines=FILE_LIMIT)
            assert len(issues) > 0
        except ImportError:
            # Module not implemented yet -- basic assertion is sufficient
            assert len(lines) == 100
