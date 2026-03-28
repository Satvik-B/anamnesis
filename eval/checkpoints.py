"""Checkpoint assertions for MemoryBench sessions.

Each checkpoint tests whether Claude recalled specific knowledge from
prior sessions, proving the memory system is working.
"""

from __future__ import annotations

import re


def _contains_any(text: str, keywords: list[str]) -> bool:
    """Check if text contains any of the keywords (case-insensitive)."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def _contains_all(text: str, keywords: list[str]) -> bool:
    """Check if text contains all of the keywords (case-insensitive)."""
    text_lower = text.lower()
    return all(kw.lower() in text_lower for kw in keywords)


# ---------------------------------------------------------------------------
# Session 2 checkpoints: Does Claude recall S1 architecture?
# ---------------------------------------------------------------------------

def s2_recalls_middleware_pattern(response: str) -> bool:
    """Claude should reference the decorator-based auth middleware from S1."""
    return _contains_any(response, [
        "decorator",
        "middleware",
        "@require_auth",
        "auth decorator",
        "existing middleware",
        "similar to auth",
    ])


def s2_recalls_app_factory(response: str) -> bool:
    """Claude should reference the application factory pattern from S1."""
    return _contains_any(response, [
        "create_app",
        "app factory",
        "application factory",
    ])


# ---------------------------------------------------------------------------
# Session 3 checkpoints: Does Claude correctly identify the bug?
# ---------------------------------------------------------------------------

def s3_identifies_race_condition(response: str) -> bool:
    """Claude should identify the concurrency/race condition issue."""
    return _contains_any(response, [
        "race condition",
        "thread safety",
        "concurrent access",
        "not thread-safe",
        "TOCTOU",
        "check-then-act",
    ])


def s3_proposes_lock_fix(response: str) -> bool:
    """Claude should propose a locking mechanism as the fix."""
    return _contains_any(response, [
        "threading.Lock",
        "Lock()",
        "mutex",
        "synchroniz",
        "atomic",
        "with lock",
    ])


def s3_identifies_multiworker_issue(response: str) -> bool:
    """Claude should note that in-memory dict doesn't share across workers."""
    return _contains_any(response, [
        "separate process",
        "each worker",
        "not shared",
        "own memory",
        "per-process",
        "Redis",
        "shared storage",
        "centralized store",
    ])


# ---------------------------------------------------------------------------
# Session 4 checkpoints: Does Claude reuse S3 learnings?
# ---------------------------------------------------------------------------

def s4_proactively_addresses_concurrency(response: str) -> bool:
    """Claude should proactively mention concurrency/threading concerns
    without being prompted — reusing the lesson from S3."""
    return _contains_any(response, [
        "race condition",
        "thread-safe",
        "threading.Lock",
        "Lock()",
        "concurrent",
        "we encountered",
        "same issue",
        "learned",
        "previous",
    ])


def s4_uses_shared_store_or_lock(response: str) -> bool:
    """Claude should use a lock or shared store in the implementation."""
    return _contains_any(response, [
        "Lock()",
        "threading.Lock",
        "Redis",
        "shared",
        "centralized",
        "with self._lock",
        "with lock",
    ])


# ---------------------------------------------------------------------------
# Session 5 checkpoints: Does Claude recall across all sessions?
# ---------------------------------------------------------------------------

def s5_mentions_jwt_auth(response: str) -> bool:
    """Summary should mention JWT authentication."""
    return _contains_any(response, [
        "JWT",
        "PyJWT",
        "token-based auth",
        "JSON Web Token",
    ])


def s5_mentions_rate_limiting(response: str) -> bool:
    """Summary should mention rate limiting."""
    return _contains_any(response, [
        "rate limit",
        "throttl",
        "429",
        "requests per minute",
    ])


def s5_mentions_race_condition_gotcha(response: str) -> bool:
    """Summary should mention the race condition as a known gotcha."""
    return _contains_any(response, [
        "race condition",
        "concurrency",
        "thread safety",
        "not thread-safe",
    ])


def s5_mentions_multiworker_caveat(response: str) -> bool:
    """Summary should mention the multi-worker memory limitation."""
    return _contains_any(response, [
        "worker",
        "gunicorn",
        "per-process",
        "not shared across",
        "Redis",
        "centralized",
    ])


# ---------------------------------------------------------------------------
# Checkpoint registry
# ---------------------------------------------------------------------------

# Maps session_number -> list of (checkpoint_name, function)
CHECKPOINTS: dict[int, list[tuple[str, callable]]] = {
    2: [
        ("s2_recalls_middleware_pattern", s2_recalls_middleware_pattern),
        ("s2_recalls_app_factory", s2_recalls_app_factory),
    ],
    3: [
        ("s3_identifies_race_condition", s3_identifies_race_condition),
        ("s3_proposes_lock_fix", s3_proposes_lock_fix),
        ("s3_identifies_multiworker_issue", s3_identifies_multiworker_issue),
    ],
    4: [
        ("s4_proactively_addresses_concurrency", s4_proactively_addresses_concurrency),
        ("s4_uses_shared_store_or_lock", s4_uses_shared_store_or_lock),
    ],
    5: [
        ("s5_mentions_jwt_auth", s5_mentions_jwt_auth),
        ("s5_mentions_rate_limiting", s5_mentions_rate_limiting),
        ("s5_mentions_race_condition_gotcha", s5_mentions_race_condition_gotcha),
        ("s5_mentions_multiworker_caveat", s5_mentions_multiworker_caveat),
    ],
}


def score_session(session_num: int, response: str) -> dict[str, bool]:
    """Run all checkpoints for a session and return results."""
    results = {}
    for name, fn in CHECKPOINTS.get(session_num, []):
        results[name] = fn(response)
    return results


def total_score(all_results: dict[int, dict[str, bool]]) -> float:
    """Compute overall retrieval accuracy (0.0 - 1.0)."""
    total = 0
    passed = 0
    for session_results in all_results.values():
        for name, result in session_results.items():
            total += 1
            if result:
                passed += 1
    return passed / total if total > 0 else 0.0
