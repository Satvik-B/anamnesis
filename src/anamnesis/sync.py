"""Sync utilities — read Claude Code sessions and write memory files.

Provides helper functions for the CLI (`anamnesis sync`) and the Claude Code
skill (`/memory sync`).  The actual *understanding* of session content is done
by Claude inside the skill; this module handles the structural I/O.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from anamnesis.ledger import Ledger
from anamnesis.project import get_auto_memory_dir, _sanitize_path_for_claude


# ── Session discovery ────────────────────────────────────────────────────────

@dataclass
class SessionInfo:
    """Metadata about a single Claude Code session file."""

    session_id: str
    path: Path
    size_bytes: int
    message_count: int = 0


def _sessions_dir(project_root: Path) -> Path:
    """Return the Claude Code project directory that holds session JSONL files."""
    slug = _sanitize_path_for_claude(str(project_root))
    return Path.home() / ".claude" / "projects" / slug


def list_sessions(project_root: Path) -> list[SessionInfo]:
    """List all session JSONL files for this project, newest first."""
    sdir = _sessions_dir(project_root)
    if not sdir.exists():
        return []

    sessions: list[SessionInfo] = []
    for f in sorted(sdir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        sessions.append(SessionInfo(
            session_id=f.stem,
            path=f,
            size_bytes=f.stat().st_size,
        ))
    return sessions


def list_unprocessed(project_root: Path, memory_dir: Path) -> list[SessionInfo]:
    """Return sessions that have not yet been processed according to the ledger."""
    ledger = Ledger.load(memory_dir)
    return [s for s in list_sessions(project_root) if not ledger.is_processed(s.session_id)]


def content_hash(path: Path) -> str:
    """Compute a SHA-256 hash of a session file for change detection."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ── Session reading ──────────────────────────────────────────────────────────

def read_session(path: Path, max_messages: int = 200) -> str:
    """Parse a session JSONL file into human-readable conversation text.

    Extracts user and assistant messages, skipping tool results and system
    messages.  Returns a plain-text transcript capped at *max_messages*.
    """
    lines: list[str] = []
    count = 0

    with open(path) as f:
        for raw_line in f:
            if count >= max_messages:
                break
            try:
                entry = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            msg = entry.get("message", {})
            role = msg.get("role")
            if role not in ("user", "assistant"):
                continue

            content = msg.get("content", "")
            if isinstance(content, list):
                # Multi-part content — extract text blocks
                text_parts = [
                    p.get("text", "")
                    for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                ]
                content = "\n".join(text_parts)
            if isinstance(content, str) and content.strip():
                lines.append(f"[{role}]: {content.strip()}")
                count += 1

    return "\n\n".join(lines)


# ── Memory writing ───────────────────────────────────────────────────────────

def write_memory(
    memory_dir: Path,
    memory_type: str,
    title: str,
    content: str,
    tags: list[str] | None = None,
    importance: str = "medium",
) -> Path:
    """Write a new memory file to the appropriate subdirectory.

    Returns the path to the created file.
    """
    slug = _slugify(title)
    type_dir = memory_dir / f"{memory_type}s"
    type_dir.mkdir(parents=True, exist_ok=True)

    dest = type_dir / f"{slug}.md"
    counter = 2
    while dest.exists():
        dest = type_dir / f"{slug}-{counter}.md"
        counter += 1

    today = date.today().isoformat()
    fm = {
        "type": memory_type,
        "tags": tags or [],
        "created": today,
        "last_accessed": today,
        "access_count": 1,
        "importance": importance,
        "source": "sync",
    }
    frontmatter = yaml.dump(fm, default_flow_style=False).strip()

    body = f"# {title}\n\n## Quick Reference\n{content[:200]}\n\n## Content\n{content}\n"
    dest.write_text(f"---\n{frontmatter}\n---\n\n{body}", encoding="utf-8")
    return dest


def _slugify(text: str) -> str:
    """Convert a title to a filename-safe slug."""
    slug = text.lower().strip()
    slug = "".join(c if c.isalnum() or c in (" ", "-") else "" for c in slug)
    slug = "-".join(slug.split())
    return slug[:60] or "memory"
