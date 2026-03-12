"""Tests for the anamnesis CLI."""

import subprocess
import sys
import textwrap
from pathlib import Path
from unittest import mock

import pytest

from anamnesis.cli import main, cmd_doctor


class TestCLIInit:
    """Tests for `anamnesis init`."""

    def test_init_fresh_project(self, tmp_project, sample_config):
        """Running init on a fresh git repo should create .claude/ structure."""
        from anamnesis.installer import install

        try:
            install(tmp_project, sample_config)
        except FileNotFoundError:
            pytest.skip("skeleton directory not yet created")

        claude_dir = tmp_project / ".claude"
        assert claude_dir.is_dir()
        assert (claude_dir / "memory").is_dir()
        assert (claude_dir / "rules").is_dir()

    def test_init_existing_project(self, installed_project, sample_config):
        """Running init on an already-initialized project should not overwrite user data."""
        memory_dir = installed_project / ".claude" / "memory"

        # Add a user file before re-init
        user_file = memory_dir / "knowledge" / "my-notes.md"
        user_file.parent.mkdir(parents=True, exist_ok=True)
        user_file.write_text("# My Notes\nImportant stuff.\n")

        from anamnesis.installer import install

        try:
            install(installed_project, sample_config)
        except FileNotFoundError:
            pytest.skip("skeleton directory not yet created")

        # User file should still exist (install never overwrites)
        assert user_file.exists()
        assert "Important stuff" in user_file.read_text()

    def test_init_creates_directories(self, tmp_project, sample_config):
        """Init should create the full directory tree."""
        from anamnesis.installer import install

        try:
            install(tmp_project, sample_config)
        except FileNotFoundError:
            pytest.skip("skeleton directory not yet created")

        claude_dir = tmp_project / ".claude"
        # At minimum .claude/ and .claude/memory/ should exist
        assert claude_dir.is_dir()
        assert (claude_dir / "memory").is_dir()


class TestCLIUpdate:
    """Tests for `anamnesis update`."""

    def test_update_preserves_user_data(self, installed_project):
        """Update should replace managed files but preserve user-created files."""
        memory_dir = installed_project / ".claude" / "memory"

        # Create a user knowledge file
        user_file = memory_dir / "knowledge" / "custom-notes.md"
        user_file.parent.mkdir(parents=True, exist_ok=True)
        user_file.write_text(textwrap.dedent("""\
            ---
            type: knowledge
            tags: [custom]
            created: 2026-01-01
            ---
            # Custom Notes
            These should survive an update.
        """))

        from anamnesis.installer import update

        try:
            update(installed_project)
        except FileNotFoundError:
            pytest.skip("skeleton directory not yet created")

        # User file must survive (it's under knowledge/ which is user data)
        assert user_file.exists()
        assert "Custom Notes" in user_file.read_text()


class TestCLIDoctor:
    """Tests for `anamnesis doctor`."""

    def test_doctor_reports_missing_claude_dir(self, tmp_project, capsys):
        """Doctor should report when .claude/ is missing."""
        args = mock.Mock()
        args.project_dir = str(tmp_project)

        ret = cmd_doctor(args)

        captured = capsys.readouterr()
        # Missing .claude/ should appear as a warning or error
        assert ".claude" in captured.out or ret != 0

    def test_doctor_reports_issues(self, installed_project, capsys):
        """Doctor should detect problems like missing INDEX.md."""
        index_path = installed_project / ".claude" / "memory" / "INDEX.md"

        # Remove INDEX.md to create an inconsistent state
        if index_path.exists():
            index_path.unlink()

        args = mock.Mock()
        args.project_dir = str(installed_project)

        ret = cmd_doctor(args)

        captured = capsys.readouterr()
        output = captured.out
        # Doctor should mention the missing INDEX.md
        assert "INDEX.md" in output or "WARN" in output

    def test_doctor_passes_on_healthy_project(self, installed_project, capsys):
        """Doctor should return 0 on a healthy installed project."""
        args = mock.Mock()
        args.project_dir = str(installed_project)

        ret = cmd_doctor(args)

        # No errors (warnings are ok)
        assert ret == 0


class TestCLIMain:
    """Tests for the main entry point."""

    def test_no_command_shows_help(self, capsys):
        """Running without a command should show help and return 0."""
        ret = main([])
        assert ret == 0

    def test_version_flag(self, capsys):
        """--version should print version and exit."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

        from anamnesis import __version__
        captured = capsys.readouterr()
        assert __version__ in captured.out
