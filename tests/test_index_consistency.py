"""Tests for INDEX.md consistency and frontmatter validation."""

import re
from pathlib import Path

import pytest
import yaml


REQUIRED_FRONTMATTER_FIELDS = {"type", "tags", "created"}


def _parse_frontmatter(path: Path) -> dict | None:
    """Extract YAML frontmatter from a markdown file."""
    text = path.read_text()
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return None
    return yaml.safe_load(match.group(1))


class TestFrontmatter:
    """Tests for memory file frontmatter."""

    def test_frontmatter_required_fields(self, fixtures_dir):
        """Every sample memory file should have the required frontmatter fields."""
        sample_dir = fixtures_dir / "sample_memory"
        md_files = list(sample_dir.rglob("*.md"))

        # Exclude INDEX.md which has a different format
        md_files = [f for f in md_files if f.name != "INDEX.md"]

        assert len(md_files) > 0, "No sample memory files found in fixtures"

        for md_file in md_files:
            fm = _parse_frontmatter(md_file)
            assert fm is not None, f"{md_file.name} has no frontmatter"
            missing = REQUIRED_FRONTMATTER_FIELDS - set(fm.keys())
            assert not missing, f"{md_file.name} missing frontmatter fields: {missing}"

    def test_sample_task_has_valid_type(self, fixtures_dir):
        """Sample task file should have type: task."""
        task_file = fixtures_dir / "sample_memory" / "tasks" / "sample-task.md"
        assert task_file.exists(), "Sample task fixture missing"

        fm = _parse_frontmatter(task_file)
        assert fm is not None
        assert fm.get("type") == "task"

    def test_sample_knowledge_has_valid_type(self, fixtures_dir):
        """Sample knowledge file should have type: knowledge."""
        knowledge_file = fixtures_dir / "sample_memory" / "knowledge" / "sample-knowledge.md"
        assert knowledge_file.exists(), "Sample knowledge fixture missing"

        fm = _parse_frontmatter(knowledge_file)
        assert fm is not None
        assert fm.get("type") == "knowledge"


class TestIndexStructure:
    """Tests for INDEX.md structure."""

    def test_index_has_table_headers(self, fixtures_dir):
        """INDEX.md should contain markdown table headers."""
        index_file = fixtures_dir / "sample_memory" / "INDEX.md"
        assert index_file.exists(), "Sample INDEX.md fixture missing"

        content = index_file.read_text()
        assert "|" in content, "INDEX.md should contain markdown tables"
        assert "File" in content, "INDEX.md tables should have a File column"

    def test_index_entries_point_to_existing_files(self, fixtures_dir):
        """Every file referenced in INDEX.md should exist in the fixture directory."""
        index_file = fixtures_dir / "sample_memory" / "INDEX.md"
        content = index_file.read_text()

        # Extract file paths from markdown table rows (format: | path | ... |)
        file_refs = re.findall(r"\|\s*(\S+\.md)\s*\|", content)

        sample_dir = fixtures_dir / "sample_memory"
        for ref in file_refs:
            ref_path = sample_dir / ref
            assert ref_path.exists(), f"INDEX.md references {ref} but file does not exist"
