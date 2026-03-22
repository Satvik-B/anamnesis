"""Install and update skeleton files into a project."""

from __future__ import annotations

import importlib.resources
import shutil
from pathlib import Path
from typing import Any

from anamnesis import __version__
from anamnesis.config import Config


# Sentinel written after install so we know which version was installed
VERSION_FILE = ".claude/.anamnesis-version"

# Files that should never be overwritten on update (user-editable data)
USER_DATA_GLOBS = [
    "memory/MEMORY.md",
    "memory/INDEX.md",
    "memory/contexts/*",
    "memory/knowledge/*",
    "memory/reflections/*",
    "memory/tasks/*",
    "memory/slack/*",
]


def _skeleton_root() -> Path:
    """Return the path to the skeleton/ directory bundled with this package.

    For editable/dev installs, the skeleton lives at the repo root (../../../skeleton
    relative to this file). For installed packages, it would be bundled as package data.
    """
    # 1. Check relative to this source file (editable install / dev checkout)
    this_file = Path(__file__).resolve()
    # src/anamnesis/installer.py -> repo root is 3 levels up
    repo_root = this_file.parent.parent.parent
    dev_skeleton = repo_root / "skeleton"
    if dev_skeleton.is_dir():
        return dev_skeleton

    # 2. importlib.resources for installed packages
    try:
        ref = importlib.resources.files("anamnesis") / "skeleton"
        if hasattr(ref, "_path"):
            p = Path(ref._path)
            if p.is_dir():
                return p
        with importlib.resources.as_file(ref) as p:
            if Path(p).is_dir():
                return Path(p)
    except (TypeError, FileNotFoundError):
        pass

    raise FileNotFoundError(
        "Skeleton directory not found. Checked:\n"
        f"  - {dev_skeleton}\n"
        "  - importlib.resources (package data)"
    )


def _render_template(content: str, context: dict[str, str]) -> str:
    """Replace {{key}} placeholders with values from context."""
    result = content
    for key, value in context.items():
        result = result.replace("{{" + key + "}}", value)
    return result


def _template_context(config: Config) -> dict[str, str]:
    """Build the template context dict from a Config."""
    return {
        "user_name": config.user_name,
        "user_role": config.user_role,
        "version": __version__,
    }


def _is_user_data(rel_path: str) -> bool:
    """Check if a relative path matches any user-data glob pattern."""
    from fnmatch import fnmatch
    for pattern in USER_DATA_GLOBS:
        if fnmatch(rel_path, pattern):
            return True
    return False


def backup_claude_dir(project_dir: Path) -> Path | None:
    """Back up .claude/ to .claude.anamnesis-backup-<timestamp>/ before changes.

    Returns the backup path if a backup was created, None if .claude/ didn't exist.
    """
    from datetime import datetime

    claude_dir = project_dir / ".claude"
    if not claude_dir.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = project_dir / f".claude.anamnesis-backup-{timestamp}"
    shutil.copytree(claude_dir, backup_dir)
    return backup_dir


def install(project_dir: Path, config: Config) -> list[str]:
    """Copy skeleton files into project_dir/.claude/, rendering templates.

    Returns a list of files that were created.
    Never overwrites existing files.
    """
    skeleton = _skeleton_root()
    if not skeleton.exists():
        raise FileNotFoundError(f"Skeleton directory not found: {skeleton}")

    target_base = project_dir / ".claude"
    target_base.mkdir(parents=True, exist_ok=True)

    context = _template_context(config)
    created: list[str] = []

    for src_file in sorted(skeleton.rglob("*")):
        if src_file.is_dir():
            continue

        rel = src_file.relative_to(skeleton)
        dest = target_base / rel

        if dest.exists():
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)

        # Only template text files
        if src_file.suffix in (".md", ".yaml", ".yml", ".txt", ".toml"):
            content = src_file.read_text(encoding="utf-8")
            content = _render_template(content, context)
            dest.write_text(content, encoding="utf-8")
        else:
            shutil.copy2(src_file, dest)

        created.append(str(rel))

    # Write version file
    version_path = project_dir / VERSION_FILE
    version_path.parent.mkdir(parents=True, exist_ok=True)
    version_path.write_text(__version__ + "\n", encoding="utf-8")

    return created


def update(project_dir: Path) -> tuple[list[str], list[str]]:
    """Update rule and skill files without touching user data.

    Returns (updated_files, skipped_files).
    """
    skeleton = _skeleton_root()
    if not skeleton.exists():
        raise FileNotFoundError(f"Skeleton directory not found: {skeleton}")

    target_base = project_dir / ".claude"
    updated: list[str] = []
    skipped: list[str] = []

    for src_file in sorted(skeleton.rglob("*")):
        if src_file.is_dir():
            continue

        rel = src_file.relative_to(skeleton)
        rel_str = str(rel)

        # Never overwrite user data
        if _is_user_data(rel_str):
            dest = target_base / rel
            if dest.exists():
                skipped.append(rel_str)
            continue

        dest = target_base / rel
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Overwrite rules/skills with latest version
        if src_file.suffix in (".md", ".yaml", ".yml", ".txt", ".toml"):
            content = src_file.read_text(encoding="utf-8")
            dest.write_text(content, encoding="utf-8")
        else:
            shutil.copy2(src_file, dest)

        updated.append(rel_str)

    # Update version file
    version_path = project_dir / VERSION_FILE
    version_path.write_text(__version__ + "\n", encoding="utf-8")

    return updated, skipped
