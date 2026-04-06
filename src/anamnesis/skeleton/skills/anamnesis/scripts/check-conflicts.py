#!/usr/bin/env python3
"""Check for conflicts between a proposed memory and existing ones.

Usage: python3 check-conflicts.py --memory-dir <path> --title <title> [--tags tag1,tag2]
       Content is read from stdin to avoid shell escaping issues.

Outputs JSON to stdout.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    memory_dir = _get_arg("--memory-dir")
    title = _get_arg("--title")
    tags_str = _get_arg("--tags") or ""
    memory_type = _get_arg("--type") or "knowledge"

    if not memory_dir or not title:
        print("Usage: check-conflicts.py --memory-dir <path> --title <title> [--tags t1,t2] [--type knowledge]", file=sys.stderr)
        print("Content is read from stdin.", file=sys.stderr)
        return 1

    try:
        from anamnesis.conflict import find_conflicts
    except ImportError:
        print(json.dumps({"error": "anamnesis not installed"}))
        return 1

    # Read content from stdin
    content = sys.stdin.read().strip() if not sys.stdin.isatty() else ""
    tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

    memory_path = Path(memory_dir)
    conflicts = find_conflicts(
        title=title,
        content=content,
        tags=tags,
        memory_type=memory_type,
        memory_dir=memory_path,
    )

    result = {
        "conflicts": [
            {
                "file": str(c.existing.path),
                "title": c.existing.title,
                "similarity": round(c.similarity, 2),
                "overlap_type": c.overlap_type,
                "strategy": c.suggested_strategy.value,
            }
            for c in conflicts
        ],
        "total": len(conflicts),
    }

    print(json.dumps(result, indent=2))
    return 0


def _get_arg(flag: str) -> str | None:
    for i, arg in enumerate(sys.argv):
        if arg == flag and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


if __name__ == "__main__":
    sys.exit(main())
