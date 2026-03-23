"""Integration tests for full CLI workflows."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest import mock

import pytest

from anamnesis import __version__
from anamnesis.cli import main, cmd_init
from anamnesis.config import Config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_init(project_dir: Path, auto: bool = False) -> int:
    """Run cmd_init with a mock config, bypassing interactive prompts."""
    config = Config(user_name="Test", user_role="dev", modules=["memory"])

    with mock.patch("anamnesis.config.collect_config_interactive", return_value=config), \
         mock.patch("anamnesis.config.save_config"):
        args = mock.Mock()
        args.project_dir = str(project_dir)
        args.auto = auto
        return cmd_init(args)


# ---------------------------------------------------------------------------
# Init integration
# ---------------------------------------------------------------------------

class TestInitIntegration:
    """End-to-end tests for `anamnesis init`."""

    def test_init_creates_full_structure(self, tmp_project):
        """Init should create all expected directories and files."""
        ret = _run_init(tmp_project)
        assert ret == 0

        claude = tmp_project / ".claude"
        assert (claude / "memory" / "INDEX.md").exists()
        assert (claude / "rules" / "memory-rule.md").exists()
        assert (claude / "skills" / "anamnesis" / "SKILL.md").exists()
        assert (claude / ".anamnesis-version").exists()

        # Memory subdirectories (only dirs with skeleton files get created)
        for subdir in ["archive", "slack"]:
            assert (claude / "memory" / subdir).is_dir(), f"Missing memory/{subdir}/"

    def test_init_creates_backup(self, installed_project):
        """Re-running init should create a backup of existing .claude/."""
        ret = _run_init(installed_project)
        assert ret == 0

        backups = list(installed_project.glob(".claude.anamnesis-backup-*"))
        assert len(backups) >= 1, "Expected a backup directory"

    def test_init_is_idempotent(self, tmp_project):
        """Running init twice should not fail or duplicate files."""
        ret1 = _run_init(tmp_project)
        assert ret1 == 0

        # Add a user file
        user_file = tmp_project / ".claude" / "memory" / "knowledge" / "my-notes.md"
        user_file.parent.mkdir(parents=True, exist_ok=True)
        user_file.write_text("# My Notes\nKeep this.\n")

        ret2 = _run_init(tmp_project)
        assert ret2 == 0

        # User file must survive
        assert user_file.exists()
        assert "Keep this" in user_file.read_text()

    def test_init_auto_mode(self, tmp_project):
        """--auto should skip interactive prompts when config exists."""
        from anamnesis.config import save_config, CONFIG_PATH

        config = Config(user_name="AutoUser", user_role="eng", modules=["memory"])

        # Pre-create config so --auto can find it
        save_config(config)

        try:
            args = mock.Mock()
            args.project_dir = str(tmp_project)
            args.auto = True

            with mock.patch("anamnesis.config.collect_config_interactive") as mock_collect:
                ret = cmd_init(args)

            assert ret == 0
            # In auto mode with existing config, interactive collection is NOT called
            mock_collect.assert_not_called()
        finally:
            # Clean up global config
            if CONFIG_PATH.exists():
                CONFIG_PATH.unlink()

    def test_init_version_matches(self, tmp_project):
        """Version file should match the installed package version."""
        _run_init(tmp_project)

        version_file = tmp_project / ".claude" / ".anamnesis-version"
        assert version_file.read_text().strip() == __version__


# ---------------------------------------------------------------------------
# Update integration
# ---------------------------------------------------------------------------

class TestUpdateIntegration:
    """End-to-end tests for `anamnesis update`."""

    def test_update_refreshes_skill(self, installed_project):
        """Update should refresh SKILL.md with latest content."""
        skill_path = installed_project / ".claude" / "skills" / "anamnesis" / "SKILL.md"
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text("# Old skill content\n")

        from anamnesis.installer import update
        updated, skipped = update(installed_project)

        # SKILL.md should have been updated (not in USER_DATA_GLOBS)
        assert any("SKILL.md" in f for f in updated), (
            f"SKILL.md not in updated list: {updated}"
        )
        content = skill_path.read_text()
        assert "Old skill content" not in content

    def test_update_refreshes_rule(self, installed_project):
        """Update should refresh memory-rule.md."""
        rule_path = installed_project / ".claude" / "rules" / "memory-rule.md"
        rule_path.write_text("# Old rule\n")

        from anamnesis.installer import update
        updated, _ = update(installed_project)

        assert any("memory-rule.md" in f for f in updated)
        content = rule_path.read_text()
        assert "Old rule" not in content

    def test_update_preserves_all_user_data(self, installed_project):
        """Update must never touch files in user-data directories."""
        memory_dir = installed_project / ".claude" / "memory"

        # Create files in every user-data subdirectory
        user_files = {}
        for subdir in ["knowledge", "contexts", "tasks", "reflections"]:
            f = memory_dir / subdir / "user-file.md"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(f"# User data in {subdir}\n")
            user_files[subdir] = f

        from anamnesis.installer import update
        update(installed_project)

        for subdir, f in user_files.items():
            assert f.exists(), f"User file in {subdir}/ was deleted by update"
            assert f"User data in {subdir}" in f.read_text()


# ---------------------------------------------------------------------------
# Doctor integration
# ---------------------------------------------------------------------------

class TestDoctorIntegration:
    """End-to-end tests for `anamnesis doctor`."""

    def test_doctor_healthy_project(self, tmp_project, capsys):
        """Doctor on a freshly initialized project should pass."""
        _run_init(tmp_project)

        args = mock.Mock()
        args.project_dir = str(tmp_project)

        from anamnesis.cli import cmd_doctor
        ret = cmd_doctor(args)

        assert ret == 0
        output = capsys.readouterr().out
        assert "ERROR" not in output

    def test_doctor_detects_missing_memory_dir(self, tmp_project, capsys):
        """Doctor should flag when .claude/memory/ is missing."""
        # Create .claude/ but not memory/
        (tmp_project / ".claude").mkdir()

        args = mock.Mock()
        args.project_dir = str(tmp_project)

        from anamnesis.cli import cmd_doctor
        cmd_doctor(args)

        output = capsys.readouterr().out
        assert "memory" in output.lower()

    def test_doctor_detects_oversized_index(self, tmp_project, capsys):
        """Doctor should warn when INDEX.md exceeds 150 lines."""
        _run_init(tmp_project)

        index = tmp_project / ".claude" / "memory" / "INDEX.md"
        index.write_text("\n".join(f"Line {i}" for i in range(160)))

        args = mock.Mock()
        args.project_dir = str(tmp_project)

        from anamnesis.cli import cmd_doctor
        cmd_doctor(args)

        output = capsys.readouterr().out
        assert "160" in output or "150" in output


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

class TestMainEntryPoint:
    """Tests for the `main()` dispatcher."""

    def test_init_via_main(self, tmp_project):
        """main(['init', '--project-dir', ...]) should work."""
        config = Config(user_name="Test", user_role="dev", modules=["memory"])
        with mock.patch("anamnesis.config.collect_config_interactive", return_value=config), \
             mock.patch("anamnesis.config.save_config"):
            ret = main(["init", "--project-dir", str(tmp_project)])
        assert ret == 0

    def test_doctor_via_main(self, installed_project, capsys):
        """main(['doctor', '--project-dir', ...]) should work."""
        ret = main(["doctor", "--project-dir", str(installed_project)])
        assert ret == 0

    def test_update_via_main(self, installed_project):
        """main(['update', '--project-dir', ...]) should work."""
        ret = main(["update", "--project-dir", str(installed_project)])
        assert ret == 0
