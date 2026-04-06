"""Tests for conflict detection and resolution."""

from pathlib import Path

import pytest

from anamnesis.conflict import (
    ConflictResult,
    MemoryFile,
    Strategy,
    compute_content_similarity,
    compute_title_similarity,
    find_conflicts,
    merge_memories,
    parse_memory_file,
    suggest_strategy,
)

SAMPLE_MEMORY = """\
---
type: knowledge
tags: [api, auth]
created: 2026-03-15
last_accessed: 2026-04-01
access_count: 5
importance: high
---

# API Authentication

## Quick Reference
Use bearer tokens for all API calls.

## Content
The auth service uses JWT tokens with 1h expiry.

## Gotchas
- Tokens don't refresh automatically
"""


def _write_memory(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


class TestParseMemoryFile:
    def test_parse_memory_file(self, tmp_path: Path):
        p = _write_memory(tmp_path, "auth.md", SAMPLE_MEMORY)
        mf = parse_memory_file(p)

        assert mf.path == p
        assert mf.memory_type == "knowledge"
        assert mf.tags == ["api", "auth"]
        assert mf.title == "API Authentication"
        assert "JWT tokens" in mf.content
        assert mf.created == "2026-03-15"
        assert mf.access_count == 5
        assert mf.importance == "high"

    def test_parse_memory_file_no_frontmatter(self, tmp_path: Path):
        raw = "# Just a Title\n\nSome content without frontmatter.\n"
        p = _write_memory(tmp_path, "plain.md", raw)
        mf = parse_memory_file(p)

        assert mf.title == "Just a Title"
        assert mf.memory_type == ""
        assert mf.tags == []
        assert mf.access_count == 0


class TestTitleSimilarity:
    def test_identical(self):
        assert compute_title_similarity("API Authentication", "API Authentication") == 1.0

    def test_similar(self):
        sim = compute_title_similarity("API Authentication Guide", "API Auth Guide")
        assert 0.4 < sim < 1.0

    def test_different(self):
        sim = compute_title_similarity("API Authentication", "Database Migration")
        assert sim < 0.3

    def test_empty(self):
        assert compute_title_similarity("", "something") == 0.0
        assert compute_title_similarity("something", "") == 0.0


class TestContentSimilarity:
    def test_identical(self):
        text = "The auth service uses JWT bearer tokens for API calls"
        assert compute_content_similarity(text, text) == 1.0

    def test_partial_overlap(self):
        a = "JWT tokens expire after one hour and need manual refresh"
        b = "JWT tokens are issued by the auth service with automatic refresh"
        sim = compute_content_similarity(a, b)
        assert 0.1 < sim < 0.8

    def test_no_overlap(self):
        a = "database migration scripts run nightly"
        b = "frontend components render user profile"
        sim = compute_content_similarity(a, b)
        assert sim < 0.2

    def test_empty(self):
        assert compute_content_similarity("", "something") == 0.0


class TestFindConflicts:
    def test_exact_duplicate(self, tmp_path: Path):
        _write_memory(tmp_path, "auth.md", SAMPLE_MEMORY)

        conflicts = find_conflicts(
            title="API Authentication",
            content="Use bearer tokens for all API calls. JWT tokens with 1h expiry.",
            tags=["api", "auth"],
            memory_type="knowledge",
            memory_dir=tmp_path,
        )

        assert len(conflicts) == 1
        assert conflicts[0].similarity > 0.7
        assert conflicts[0].suggested_strategy in (Strategy.SKIP, Strategy.MERGE)

    def test_related(self, tmp_path: Path):
        _write_memory(tmp_path, "auth.md", SAMPLE_MEMORY)

        conflicts = find_conflicts(
            title="API Token Refresh",
            content="Tokens can be refreshed using the refresh endpoint with grant_type.",
            tags=["api", "tokens"],
            memory_type="knowledge",
            memory_dir=tmp_path,
        )

        # Related but not identical — may or may not produce a conflict
        # depending on word overlap; if it does, strategy should be ASK or MERGE
        for c in conflicts:
            assert c.suggested_strategy in (Strategy.ASK, Strategy.MERGE, Strategy.SKIP)

    def test_no_match(self, tmp_path: Path):
        _write_memory(tmp_path, "auth.md", SAMPLE_MEMORY)

        conflicts = find_conflicts(
            title="Database Migration Guide",
            content="Run alembic upgrade head to apply pending migrations to PostgreSQL.",
            tags=["database", "migration"],
            memory_type="task",
            memory_dir=tmp_path,
        )

        assert len(conflicts) == 0

    def test_empty_dir(self, tmp_path: Path):
        empty = tmp_path / "empty"
        empty.mkdir()

        conflicts = find_conflicts(
            title="Anything",
            content="Some content",
            tags=["tag"],
            memory_type="knowledge",
            memory_dir=empty,
        )

        assert conflicts == []

    def test_skips_index_files(self, tmp_path: Path):
        _write_memory(tmp_path, "MEMORY.md", "# Memory Index\nSome pointers.")
        _write_memory(tmp_path, "INDEX.md", "# Index\nCatalog.")
        _write_memory(tmp_path, "README.md", "# Readme\nInstructions.")

        conflicts = find_conflicts(
            title="Memory Index",
            content="Some pointers and catalog.",
            tags=[],
            memory_type="knowledge",
            memory_dir=tmp_path,
        )

        assert conflicts == []

    def test_sorted_by_similarity(self, tmp_path: Path):
        _write_memory(tmp_path, "auth.md", SAMPLE_MEMORY)
        _write_memory(
            tmp_path,
            "auth2.md",
            "---\ntype: knowledge\ntags: [api]\n---\n\n# API Auth Tokens\n\nBearer tokens used.\n",
        )

        conflicts = find_conflicts(
            title="API Authentication",
            content="Use bearer tokens for all API calls. JWT tokens with 1h expiry.",
            tags=["api", "auth"],
            memory_type="knowledge",
            memory_dir=tmp_path,
        )

        if len(conflicts) >= 2:
            assert conflicts[0].similarity >= conflicts[1].similarity


class TestMergeMemories:
    def test_merge_memories(self, tmp_path: Path):
        p = _write_memory(tmp_path, "auth.md", SAMPLE_MEMORY)
        mf = parse_memory_file(p)

        merged = merge_memories(mf, "New info about token rotation.", ["api", "rotation"])

        assert "# API Authentication" in merged
        assert "## Updated" in merged
        assert "New info about token rotation." in merged
        # Original content preserved
        assert "JWT tokens" in merged
        # Tags combined
        assert "rotation" in merged
        assert "auth" in merged

    def test_merge_preserves_frontmatter(self, tmp_path: Path):
        p = _write_memory(tmp_path, "auth.md", SAMPLE_MEMORY)
        mf = parse_memory_file(p)

        merged = merge_memories(mf, "Extra.", ["api"])

        assert merged.startswith("---\n")
        assert "type: knowledge" in merged


class TestSuggestStrategy:
    def _make_conflict(self, similarity: float) -> ConflictResult:
        mf = MemoryFile(
            path=Path("/fake.md"),
            memory_type="knowledge",
            tags=[],
            title="Test",
            content="Test content",
        )
        return ConflictResult(
            existing=mf,
            similarity=similarity,
            overlap_type="combined",
            suggested_strategy=Strategy.ASK,
        )

    def test_high_similarity_skip(self):
        assert suggest_strategy(self._make_conflict(0.85)) == Strategy.SKIP

    def test_medium_similarity_merge(self):
        assert suggest_strategy(self._make_conflict(0.7)) == Strategy.MERGE

    def test_ambiguous_similarity_ask(self):
        assert suggest_strategy(self._make_conflict(0.5)) == Strategy.ASK

    def test_boundary_08(self):
        # Exactly 0.8 should not trigger SKIP (> 0.8 required)
        assert suggest_strategy(self._make_conflict(0.8)) == Strategy.MERGE

    def test_boundary_06(self):
        # Exactly 0.6 should not trigger MERGE (> 0.6 required)
        assert suggest_strategy(self._make_conflict(0.6)) == Strategy.ASK


class TestFindConflictsSkipsArchive:
    """Invariant: find_conflicts must never match against archived memories."""

    def test_archived_memories_ignored(self, tmp_path: Path):
        # Create active memory
        _write_memory(tmp_path, "auth.md", SAMPLE_MEMORY)

        # Create archived memory with identical content
        archive_dir = tmp_path / "archive" / "2026-01"
        archive_dir.mkdir(parents=True)
        _write_memory(archive_dir, "auth-old.md", SAMPLE_MEMORY)

        conflicts = find_conflicts(
            title="API Authentication",
            content="Use bearer tokens for all API calls. JWT tokens with 1h expiry.",
            tags=["api", "auth"],
            memory_type="knowledge",
            memory_dir=tmp_path,
        )

        # Should only match the active memory, not the archived one
        matched_paths = {c.existing.path for c in conflicts}
        archive_dir = tmp_path / "archive"
        for p in matched_paths:
            assert not str(p).startswith(str(archive_dir)), f"Matched archived file: {p}"
