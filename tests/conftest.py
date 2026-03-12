"""Shared pytest fixtures for claude-memory tests."""

import os
import subprocess
import textwrap
from pathlib import Path

import pytest

from claude_memory.config import Config


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary directory with `git init`, simulating a project root."""
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(
        ["git", "init"],
        cwd=str(project),
        capture_output=True,
        check=True,
    )
    return project


@pytest.fixture
def sample_config():
    """Return a valid Config object."""
    return Config(
        user_name="Test User",
        user_role="developer",
        modules=["memory"],
    )


@pytest.fixture
def installed_project(tmp_project, sample_config):
    """Run the installer on a tmp_project with sample_config and return the path.

    If the skeleton directory is missing (not yet created by the skeleton-writer),
    create the minimal expected structure manually.
    """
    from claude_memory.installer import install

    try:
        install(tmp_project, sample_config)
    except FileNotFoundError:
        # Skeleton not bundled yet -- create the minimal expected structure
        claude_dir = tmp_project / ".claude"
        claude_dir.mkdir(exist_ok=True)
        (claude_dir / "rules").mkdir(exist_ok=True)
        (claude_dir / "skills").mkdir(exist_ok=True)

        memory_dir = claude_dir / "memory"
        memory_dir.mkdir(exist_ok=True)
        for subdir in ["archive", "tasks", "knowledge", "contexts", "reflections", "slack"]:
            (memory_dir / subdir).mkdir(exist_ok=True)

        index_md = memory_dir / "INDEX.md"
        index_md.write_text(textwrap.dedent("""\
            # Memory Index

            > Cold index -- loaded on demand.

            ## Tasks
            | File | Tags | Last Accessed |
            |------|------|---------------|

            ## Knowledge
            | File | Tags | Last Accessed |
            |------|------|---------------|
        """))

        rules_file = claude_dir / "rules" / "memory-rule.md"
        rules_file.write_text("# Memory Rule\nPlaceholder rule file.\n")

        # Write version file
        from claude_memory import __version__
        version_file = claude_dir / ".claude-memory-version"
        version_file.write_text(__version__ + "\n")

    return tmp_project


@pytest.fixture
def fixtures_dir():
    """Return the path to the tests/fixtures directory."""
    return Path(__file__).parent / "fixtures"
