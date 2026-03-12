"""Project root detection and Claude Code path utilities."""

import os
import re
from pathlib import Path


def find_project_root(start: str | None = None) -> Path | None:
    """Walk up from *start* (default: cwd) to find the nearest .git directory.

    Returns the directory containing .git, or None if no repo root is found.
    """
    current = Path(start) if start else Path.cwd()
    current = current.resolve()

    while True:
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _sanitize_path_for_claude(path: str) -> str:
    """Convert an absolute path into the slug Claude Code uses for its project directory.

    Claude Code replaces path separators with dashes and prepends a dash.
    For example: /Users/alice/myproject -> -Users-alice-myproject
    """
    # Strip trailing slash, replace / with -
    cleaned = path.rstrip("/")
    slug = cleaned.replace("/", "-")
    # On macOS/Linux the path starts with /, so slug already starts with -
    if not slug.startswith("-"):
        slug = "-" + slug
    return slug


def get_auto_memory_dir(project_root: Path | None = None) -> Path:
    """Return Claude Code's auto-memory directory for this project.

    Claude Code stores per-project auto-memory files at:
        ~/.claude/projects/<sanitized-path>/memory/

    where <sanitized-path> is the absolute project path with '/' replaced by '-'.
    """
    if project_root is None:
        project_root = find_project_root()
    if project_root is None:
        raise FileNotFoundError("Could not find a project root (.git directory)")

    slug = _sanitize_path_for_claude(str(project_root))
    return Path.home() / ".claude" / "projects" / slug / "memory"


def get_memory_md_path(project_root: Path | None = None) -> Path:
    """Return the path to the auto-loaded MEMORY.md for this project."""
    return get_auto_memory_dir(project_root) / "MEMORY.md"
