"""Tests for the session ledger module."""

from __future__ import annotations

import yaml

from anamnesis.ledger import Ledger, SessionEntry, LEDGER_FILENAME


def test_load_creates_empty_ledger(tmp_path):
    ledger = Ledger.load(tmp_path)
    assert ledger.entries == {}
    assert ledger._path == tmp_path / LEDGER_FILENAME


def test_load_existing_ledger(tmp_path):
    data = {
        "sessions": {
            "abc-123": {
                "processed_date": "2026-04-01",
                "memories_created": 3,
                "content_hash": "deadbeef",
            }
        }
    }
    (tmp_path / LEDGER_FILENAME).write_text(yaml.dump(data))

    ledger = Ledger.load(tmp_path)
    assert "abc-123" in ledger.entries
    entry = ledger.entries["abc-123"]
    assert entry.processed_date == "2026-04-01"
    assert entry.memories_created == 3
    assert entry.content_hash == "deadbeef"


def test_mark_processed_and_is_processed(tmp_path):
    ledger = Ledger.load(tmp_path)
    assert not ledger.is_processed("sess-1")

    ledger.mark_processed("sess-1", memories_created=2, content_hash="aaa")
    assert ledger.is_processed("sess-1")
    assert ledger.entries["sess-1"].memories_created == 2
    assert ledger.entries["sess-1"].content_hash == "aaa"


def test_needs_reprocessing(tmp_path):
    ledger = Ledger.load(tmp_path)

    # Unprocessed session always needs processing
    assert ledger.needs_reprocessing("sess-1", "hash-a")

    ledger.mark_processed("sess-1", content_hash="hash-a")
    assert not ledger.needs_reprocessing("sess-1", "hash-a")
    assert ledger.needs_reprocessing("sess-1", "hash-b")


def test_save_and_reload(tmp_path):
    ledger = Ledger.load(tmp_path)
    ledger.mark_processed("s1", memories_created=5, content_hash="h1")
    ledger.mark_processed("s2", memories_created=0, content_hash="h2")
    ledger.save()

    reloaded = Ledger.load(tmp_path)
    assert len(reloaded.entries) == 2
    assert reloaded.entries["s1"].memories_created == 5
    assert reloaded.entries["s2"].content_hash == "h2"


def test_get_stats(tmp_path):
    ledger = Ledger.load(tmp_path)

    # Empty stats
    stats = ledger.get_stats()
    assert stats["total_processed"] == 0
    assert stats["total_memories"] == 0
    assert stats["oldest"] is None
    assert stats["newest"] is None

    ledger.mark_processed("s1", memories_created=3, content_hash="a")
    ledger.entries["s1"].processed_date = "2026-03-01"
    ledger.mark_processed("s2", memories_created=7, content_hash="b")
    ledger.entries["s2"].processed_date = "2026-04-01"

    stats = ledger.get_stats()
    assert stats["total_processed"] == 2
    assert stats["total_memories"] == 10
    assert stats["oldest"] == "2026-03-01"
    assert stats["newest"] == "2026-04-01"


def test_mark_processed_updates_existing(tmp_path):
    ledger = Ledger.load(tmp_path)
    ledger.mark_processed("sess-1", memories_created=2, content_hash="old")
    ledger.mark_processed("sess-1", memories_created=5, content_hash="new")

    assert len(ledger.entries) == 1
    entry = ledger.entries["sess-1"]
    assert entry.memories_created == 5
    assert entry.content_hash == "new"
