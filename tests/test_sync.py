"""Tests for the sync module."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from anamnesis.sync import (
    SessionInfo,
    content_hash,
    list_sessions,
    list_unprocessed,
    read_session,
    write_memory,
    _slugify,
)
from anamnesis.ledger import Ledger


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _write_session_jsonl(path: Path, messages: list[dict]) -> None:
    with open(path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")


@pytest.fixture
def sessions_dir(tmp_path, monkeypatch):
    """Create a fake ~/.claude/projects/<slug>/ with session files."""
    slug = "-tmp-project"
    base = tmp_path / "home" / ".claude" / "projects" / slug
    base.mkdir(parents=True)

    # Patch _sessions_dir to use our tmp directory
    import anamnesis.sync as sync_mod
    original = sync_mod._sessions_dir

    def patched(project_root):
        return base

    monkeypatch.setattr(sync_mod, "_sessions_dir", patched)

    # Create two session files
    _write_session_jsonl(base / "session-aaa.jsonl", [
        {"message": {"role": "user", "content": "Hello"}},
        {"message": {"role": "assistant", "content": "Hi there!"}},
    ])
    _write_session_jsonl(base / "session-bbb.jsonl", [
        {"message": {"role": "user", "content": "How does auth work?"}},
        {"message": {"role": "assistant", "content": "It uses JWT tokens."}},
    ])

    return base


@pytest.fixture
def memory_dir(tmp_path):
    d = tmp_path / "memory"
    d.mkdir()
    return d


# ── Tests ────────────────────────────────────────────────────────────────────

class TestListSessions:
    def test_lists_jsonl_files(self, sessions_dir, tmp_path):
        sessions = list_sessions(tmp_path / "project")
        assert len(sessions) == 2
        ids = {s.session_id for s in sessions}
        assert "session-aaa" in ids
        assert "session-bbb" in ids

    def test_empty_when_no_dir(self, tmp_path, monkeypatch):
        import anamnesis.sync as sync_mod
        monkeypatch.setattr(sync_mod, "_sessions_dir", lambda _: tmp_path / "nope")
        assert list_sessions(tmp_path) == []


class TestListUnprocessed:
    def test_all_unprocessed(self, sessions_dir, memory_dir, tmp_path):
        result = list_unprocessed(tmp_path / "project", memory_dir)
        assert len(result) == 2

    def test_skip_processed(self, sessions_dir, memory_dir, tmp_path):
        ledger = Ledger.load(memory_dir)
        ledger.mark_processed("session-aaa")
        ledger.save()
        result = list_unprocessed(tmp_path / "project", memory_dir)
        assert len(result) == 1
        assert result[0].session_id == "session-bbb"


class TestReadSession:
    def test_parses_messages(self, sessions_dir):
        jsonl = sessions_dir / "session-aaa.jsonl"
        text = read_session(jsonl)
        assert "[user]: Hello" in text
        assert "[assistant]: Hi there!" in text

    def test_skips_non_messages(self, tmp_path):
        path = tmp_path / "test.jsonl"
        _write_session_jsonl(path, [
            {"type": "permission-mode", "permissionMode": "default"},
            {"message": {"role": "user", "content": "Hello"}},
            {"type": "file-history-snapshot"},
        ])
        text = read_session(path)
        assert "[user]: Hello" in text
        assert "permission" not in text

    def test_max_messages(self, tmp_path):
        path = tmp_path / "big.jsonl"
        msgs = [{"message": {"role": "user", "content": f"msg {i}"}} for i in range(300)]
        _write_session_jsonl(path, msgs)
        text = read_session(path, max_messages=5)
        assert text.count("[user]:") == 5

    def test_multi_part_content(self, tmp_path):
        path = tmp_path / "multi.jsonl"
        _write_session_jsonl(path, [
            {"message": {"role": "assistant", "content": [
                {"type": "text", "text": "First part"},
                {"type": "tool_use", "id": "abc", "name": "Bash"},
                {"type": "text", "text": "Second part"},
            ]}}
        ])
        text = read_session(path)
        assert "First part" in text
        assert "Second part" in text
        assert "tool_use" not in text


class TestContentHash:
    def test_deterministic(self, tmp_path):
        f = tmp_path / "test.jsonl"
        f.write_text("hello\n")
        h1 = content_hash(f)
        h2 = content_hash(f)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex digest

    def test_different_content(self, tmp_path):
        f1 = tmp_path / "a.jsonl"
        f2 = tmp_path / "b.jsonl"
        f1.write_text("aaa\n")
        f2.write_text("bbb\n")
        assert content_hash(f1) != content_hash(f2)


class TestWriteMemory:
    def test_creates_file(self, memory_dir):
        path = write_memory(memory_dir, "knowledge", "API Auth", "Use JWT tokens", tags=["api", "auth"])
        assert path.exists()
        assert path.parent.name == "knowledges"
        content = path.read_text()
        assert "# API Auth" in content
        assert "Use JWT tokens" in content
        assert "api" in content

    def test_avoids_name_collision(self, memory_dir):
        p1 = write_memory(memory_dir, "knowledge", "Topic", "Content 1")
        p2 = write_memory(memory_dir, "knowledge", "Topic", "Content 2")
        assert p1 != p2
        assert p1.exists()
        assert p2.exists()


class TestSlugify:
    def test_basic(self):
        assert _slugify("API Authentication") == "api-authentication"

    def test_special_chars(self):
        assert _slugify("How to: do stuff!") == "how-to-do-stuff"

    def test_truncates(self):
        long = "a " * 100
        assert len(_slugify(long)) <= 60

    def test_empty(self):
        assert _slugify("") == "memory"
