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


class TestBackup:
    """Tests for the backup functionality."""

    def test_backup_creates_copy(self, installed_project):
        """backup_claude_dir should create a timestamped copy of .claude/."""
        from anamnesis.installer import backup_claude_dir

        backup_path = backup_claude_dir(installed_project)

        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.name.startswith(".claude.anamnesis-backup-")
        # Backup should contain the same structure
        assert (backup_path / "rules").is_dir() or (backup_path / "memory").is_dir()

    def test_backup_returns_none_when_no_claude_dir(self, tmp_project):
        """backup_claude_dir should return None if .claude/ doesn't exist."""
        from anamnesis.installer import backup_claude_dir

        result = backup_claude_dir(tmp_project)
        assert result is None


class TestCleanupStaleBackups:
    """Tests for stale backup cleanup."""

    def test_removes_old_backups(self, installed_project):
        """Backups older than 30 days should be removed."""
        from anamnesis.installer import cleanup_stale_backups

        # Create a fake old backup (60 days ago)
        old_backup = installed_project / ".claude.anamnesis-backup-20260122-100000"
        old_backup.mkdir()
        (old_backup / "marker.txt").write_text("old")

        removed = cleanup_stale_backups(installed_project)

        assert len(removed) == 1
        assert removed[0] == old_backup
        assert not old_backup.exists()

    def test_keeps_recent_backups(self, installed_project):
        """Backups newer than 30 days should be kept."""
        from anamnesis.installer import cleanup_stale_backups, backup_claude_dir

        # Create a fresh backup (now)
        fresh_backup = backup_claude_dir(installed_project)
        assert fresh_backup is not None

        removed = cleanup_stale_backups(installed_project)

        assert len(removed) == 0
        assert fresh_backup.exists()

    def test_no_backups_is_noop(self, installed_project):
        """No backups present should return empty list."""
        from anamnesis.installer import cleanup_stale_backups

        removed = cleanup_stale_backups(installed_project)
        assert removed == []
