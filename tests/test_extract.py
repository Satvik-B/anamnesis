"""Tests for the extraction heuristics module."""

from __future__ import annotations

import pytest

from anamnesis.extract import (
    ExtractedMemory,
    MemoryType,
    _generate_title,
    _infer_tags,
    extract_memories,
)


class TestExtractGotcha:
    """Gotcha-type signal phrases are detected."""

    def test_gotcha_keyword(self):
        text = "There's a gotcha with the config parser.\nIt silently drops unknown keys."
        results = extract_memories(text)
        assert any(m.memory_type == MemoryType.GOTCHA for m in results)

    def test_watch_out(self):
        text = "Watch out for the rate limiter on that endpoint."
        results = extract_memories(text)
        assert any(m.memory_type == MemoryType.GOTCHA for m in results)

    def test_warning_colon_strong(self):
        text = "Warning: the migration script does not handle NULLs."
        results = extract_memories(text)
        gotchas = [m for m in results if m.memory_type == MemoryType.GOTCHA]
        assert len(gotchas) >= 1
        assert gotchas[0].confidence >= 0.8

    def test_heads_up(self):
        text = "Heads up, the staging DB is read-only on weekends."
        results = extract_memories(text)
        assert any(m.memory_type == MemoryType.GOTCHA for m in results)

    def test_workaround_colon(self):
        text = "Workaround: set the env var before importing the module."
        results = extract_memories(text)
        gotchas = [m for m in results if m.memory_type == MemoryType.GOTCHA]
        assert len(gotchas) >= 1
        assert gotchas[0].confidence >= 0.8


class TestExtractKnowledge:
    """Knowledge-type signal phrases are detected."""

    def test_til(self):
        text = "TIL that Python dicts maintain insertion order since 3.7."
        results = extract_memories(text)
        assert any(m.memory_type == MemoryType.KNOWLEDGE for m in results)

    def test_learned_that(self):
        text = "I learned that the API uses cursor-based pagination."
        results = extract_memories(text)
        assert any(m.memory_type == MemoryType.KNOWLEDGE for m in results)

    def test_turns_out(self):
        text = "Turns out the cache invalidation is done via pub/sub."
        results = extract_memories(text)
        assert any(m.memory_type == MemoryType.KNOWLEDGE for m in results)

    def test_design_decision(self):
        text = "The design decision was to use event sourcing for audit trails."
        results = extract_memories(text)
        assert any(m.memory_type == MemoryType.KNOWLEDGE for m in results)

    def test_til_colon_strong(self):
        text = "TIL: asyncio.gather swallows exceptions by default."
        results = extract_memories(text)
        knowledge = [m for m in results if m.memory_type == MemoryType.KNOWLEDGE]
        assert len(knowledge) >= 1
        assert knowledge[0].confidence >= 0.8


class TestExtractTask:
    """Task-type signal phrases are detected."""

    def test_numbered_steps(self):
        text = (
            "To deploy the service:\n"
            "1. Run the build script\n"
            "2. Push the Docker image\n"
            "3. Apply the k8s manifest\n"
        )
        results = extract_memories(text)
        assert any(m.memory_type == MemoryType.TASK for m in results)

    def test_steps_colon(self):
        text = "Steps: first pull the latest, then run migrations."
        results = extract_memories(text)
        tasks = [m for m in results if m.memory_type == MemoryType.TASK]
        assert len(tasks) >= 1
        assert tasks[0].confidence >= 0.8

    def test_how_to(self):
        text = "Here's how to reset the dev database after a bad migration."
        results = extract_memories(text)
        assert any(m.memory_type == MemoryType.TASK for m in results)

    def test_first_then_finally(self):
        text = (
            "First, stop the service.\n"
            "Then, run the cleanup script.\n"
            "Finally, restart the service."
        )
        results = extract_memories(text)
        tasks = [m for m in results if m.memory_type == MemoryType.TASK]
        assert len(tasks) >= 1


class TestExtractReflection:
    """Reflection-type signal phrases are detected."""

    def test_mistake(self):
        text = "That was a mistake — we should have tested on staging first."
        results = extract_memories(text)
        assert any(m.memory_type == MemoryType.REFLECTION for m in results)

    def test_should_have(self):
        text = "I should have checked the logs before restarting the service."
        results = extract_memories(text)
        assert any(m.memory_type == MemoryType.REFLECTION for m in results)

    def test_lesson_colon_strong(self):
        text = "Lesson: always run the linter before pushing to main."
        results = extract_memories(text)
        reflections = [m for m in results if m.memory_type == MemoryType.REFLECTION]
        assert len(reflections) >= 1
        assert reflections[0].confidence >= 0.8

    def test_in_hindsight(self):
        text = "In hindsight, the monorepo was the wrong call for this team."
        results = extract_memories(text)
        assert any(m.memory_type == MemoryType.REFLECTION for m in results)

    def test_wrong_approach(self):
        text = "That was the wrong approach. We should use a queue instead."
        results = extract_memories(text)
        assert any(m.memory_type == MemoryType.REFLECTION for m in results)


class TestConfidenceScoring:
    """Confidence values increase with signal strength."""

    def test_single_weak_signal(self):
        text = "There might be a trap in the serialization logic."
        results = extract_memories(text)
        gotchas = [m for m in results if m.memory_type == MemoryType.GOTCHA]
        assert len(gotchas) >= 1
        assert gotchas[0].confidence == pytest.approx(0.4, abs=0.15)

    def test_strong_signal_higher(self):
        text = "Warning: the API key rotates every 24 hours."
        results = extract_memories(text)
        gotchas = [m for m in results if m.memory_type == MemoryType.GOTCHA]
        assert len(gotchas) >= 1
        assert gotchas[0].confidence >= 0.8

    def test_multiple_signals_boost(self):
        text = (
            "Watch out for the caching layer.\n"
            "There's a gotcha with TTL expiration.\n"
            "Beware of stale reads after a write."
        )
        results = extract_memories(text)
        gotchas = [m for m in results if m.memory_type == MemoryType.GOTCHA]
        assert len(gotchas) >= 1
        # With multiple signals in context, confidence should be >= 0.6
        assert max(g.confidence for g in gotchas) >= 0.6

    def test_multiple_strong_signals(self):
        text = (
            "Warning: don't use the old endpoint.\n"
            "Important: the new endpoint requires auth headers."
        )
        results = extract_memories(text)
        gotchas = [m for m in results if m.memory_type == MemoryType.GOTCHA]
        assert len(gotchas) >= 1
        assert max(g.confidence for g in gotchas) >= 0.8

    def test_short_content_penalized(self):
        text = "Gotcha"
        results = extract_memories(text)
        if results:
            assert results[0].confidence < 0.4


class TestDeduplication:
    """Overlapping matches within 2 lines are consolidated."""

    def test_same_type_nearby_lines_deduped(self):
        text = (
            "Gotcha: the parser is strict.\n"
            "Watch out for trailing commas.\n"
            "Beware of unicode in keys."
        )
        results = extract_memories(text)
        gotchas = [m for m in results if m.memory_type == MemoryType.GOTCHA]
        # All three lines are within 2 lines of each other, so they should
        # be deduplicated into at most 2 entries (lines 0-1 overlap, 1-2 overlap).
        # The exact count depends on grouping, but it should be fewer than 3.
        assert len(gotchas) <= 2

    def test_different_types_not_deduped(self):
        text = (
            "Gotcha: the config format changed.\n"
            "I learned that YAML anchors can help here."
        )
        results = extract_memories(text)
        types = {m.memory_type for m in results}
        assert MemoryType.GOTCHA in types
        assert MemoryType.KNOWLEDGE in types

    def test_far_apart_not_deduped(self):
        text_lines = ["Normal line."] * 10
        text_lines[0] = "Gotcha: first issue."
        text_lines[9] = "Gotcha: second issue."
        text = "\n".join(text_lines)
        results = extract_memories(text)
        gotchas = [m for m in results if m.memory_type == MemoryType.GOTCHA]
        assert len(gotchas) == 2


class TestNoFalsePositives:
    """Normal text without signal phrases returns no memories."""

    def test_normal_prose(self):
        text = (
            "The application handles user requests through a REST API.\n"
            "Each request is validated and processed by the handler.\n"
            "Responses are returned in JSON format.\n"
            "The server runs on port 8080 by default."
        )
        results = extract_memories(text)
        assert len(results) == 0

    def test_empty_string(self):
        results = extract_memories("")
        assert len(results) == 0

    def test_whitespace_only(self):
        results = extract_memories("   \n\n   \n")
        assert len(results) == 0


class TestMultipleTypes:
    """Text with mixed memory types extracts all of them."""

    def test_mixed_gotcha_and_knowledge(self):
        text = (
            "TIL that the cache has a 5-minute TTL.\n"
            "\n"
            "Some normal text here.\n"
            "More normal text.\n"
            "Even more padding.\n"
            "\n"
            "Warning: the cache doesn't invalidate on writes."
        )
        results = extract_memories(text)
        types = {m.memory_type for m in results}
        assert MemoryType.KNOWLEDGE in types
        assert MemoryType.GOTCHA in types

    def test_mixed_task_and_reflection(self):
        text = (
            "Steps: pull, build, deploy.\n"
            "\n"
            "Some filler.\n"
            "More filler.\n"
            "Even more filler.\n"
            "\n"
            "In hindsight, we should have automated this."
        )
        results = extract_memories(text)
        types = {m.memory_type for m in results}
        assert MemoryType.TASK in types
        assert MemoryType.REFLECTION in types


class TestGenerateTitle:
    """Title generation picks a meaningful first line."""

    def test_simple_sentence(self):
        title = _generate_title("Watch out for the rate limiter.", MemoryType.GOTCHA)
        assert "rate limiter" in title.lower()

    def test_strips_numbering(self):
        title = _generate_title("1. Run the build script", MemoryType.TASK)
        assert not title.startswith("1.")
        assert "build script" in title.lower()

    def test_truncates_long_line(self):
        long_line = "A " * 100
        title = _generate_title(long_line, MemoryType.KNOWLEDGE)
        assert len(title) <= 84  # 80 + "..."

    def test_empty_content_fallback(self):
        title = _generate_title("", MemoryType.GOTCHA)
        assert title == "gotcha memory"

    def test_skips_blank_lines(self):
        title = _generate_title("\n\n\nActual content here.", MemoryType.KNOWLEDGE)
        assert "actual content" in title.lower()


class TestInferTags:
    """Tag inference detects technical terms."""

    def test_python_tag(self):
        tags = _infer_tags("The Python script handles the migration.")
        assert "python" in tags
        assert "migration" in tags

    def test_docker_kubernetes(self):
        tags = _infer_tags("Deploy the Docker container to Kubernetes.")
        assert "docker" in tags
        assert "kubernetes" in tags

    def test_k8s_alias(self):
        tags = _infer_tags("Apply the k8s manifest.")
        assert "kubernetes" in tags

    def test_no_tags_for_generic_text(self):
        tags = _infer_tags("This is a normal sentence without technical terms.")
        assert len(tags) == 0

    def test_no_duplicate_tags(self):
        tags = _infer_tags("Python and more Python code in Python files.")
        assert tags.count("python") == 1

    def test_api_and_auth(self):
        tags = _infer_tags("The API requires auth tokens for every request.")
        assert "api" in tags
        assert "auth" in tags
