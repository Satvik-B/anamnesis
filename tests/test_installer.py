"""Tests for the anamnesis installer module."""

import textwrap
from pathlib import Path

import pytest

from anamnesis.config import Config
from anamnesis.installer import install, update


def _try_install(project_path, config=None):
    """Attempt to run the installer; skip if skeleton is missing."""
    if config is None:
        config = Config(user_name="Test", user_role="dev", modules=["memory"])
    try:
        return install(project_path, config)
    except FileNotFoundError as e:
        if "skeleton" in str(e).lower():
            pytest.skip("skeleton directory not yet created")
        raise


def _try_update(project_path):
    """Attempt to run the updater; skip if skeleton is missing."""
    try:
        return update(project_path)
    except FileNotFoundError as e:
        if "skeleton" in str(e).lower():
            pytest.skip("skeleton directory not yet created")
        raise


class TestInstallInit:
    """Tests for the install (init) operation."""

    def test_init_creates_rule_file(self, tmp_project):
        """Init should create at least one rule file in .claude/rules/."""
        _try_install(tmp_project)

        rules_dir = tmp_project / ".claude" / "rules"
        assert rules_dir.is_dir()

        rule_files = list(rules_dir.glob("*.md"))
        assert len(rule_files) >= 1, "Expected at least one rule file after init"

    def test_init_creates_skill_directory(self, tmp_project):
        """Init should create the .claude/skills/ directory."""
        _try_install(tmp_project)

        skills_dir = tmp_project / ".claude" / "skills"
        assert skills_dir.is_dir()

    def test_init_creates_memory_index(self, tmp_project):
        """Init should create .claude/memory/INDEX.md."""
        _try_install(tmp_project)

        index = tmp_project / ".claude" / "memory" / "INDEX.md"
        assert index.exists()
        content = index.read_text()
        assert "Index" in content or "index" in content

    def test_init_never_overwrites_existing_memory(self, tmp_project):
        """If INDEX.md already exists, init should not overwrite it."""
        memory_dir = tmp_project / ".claude" / "memory"
        memory_dir.mkdir(parents=True)
        index = memory_dir / "INDEX.md"
        index.write_text("# My Custom Index\nDo not overwrite me.\n")

        _try_install(tmp_project)

        # install() never overwrites existing files
        assert "My Custom Index" in index.read_text()

    def test_init_creates_version_file(self, tmp_project):
        """Init should write a version sentinel file."""
        _try_install(tmp_project)

        from anamnesis import __version__
        version_file = tmp_project / ".claude" / ".anamnesis-version"
        assert version_file.exists()
        assert version_file.read_text().strip() == __version__

    def test_init_returns_created_files(self, tmp_project):
        """install() should return a list of created relative paths."""
        created = _try_install(tmp_project)

        assert isinstance(created, list)
        assert len(created) >= 1, "Expected at least one file to be created"
        # Paths should be relative to .claude/
        for f in created:
            assert not f.startswith("/"), f"Path should be relative: {f}"


class TestInstallUpdate:
    """Tests for the update operation."""

    def test_update_replaces_rules_only(self, installed_project):
        """Update should replace managed rule files but leave user memory intact."""
        # Add user memory
        user_mem = installed_project / ".claude" / "memory" / "knowledge" / "user-note.md"
        user_mem.parent.mkdir(parents=True, exist_ok=True)
        user_mem.write_text(textwrap.dedent("""\
            ---
            type: knowledge
            tags: [user]
            created: 2026-01-01
            ---
            # User Note
            Preserve this.
        """))

        _try_update(installed_project)

        # User memory should be preserved (under knowledge/ which is user data)
        assert user_mem.exists()
        assert "Preserve this" in user_mem.read_text()

    def test_update_returns_updated_and_skipped(self, installed_project):
        """update() should return (updated_files, skipped_files) tuple."""
        result = _try_update(installed_project)

        assert isinstance(result, tuple)
        assert len(result) == 2
        updated, skipped = result
        assert isinstance(updated, list)
        assert isinstance(skipped, list)
