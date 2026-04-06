#!/usr/bin/env python3
"""Find duplicate memory groups based on title and content similarity.

Usage: python3 find-duplicates.py --memory-dir <path>

Outputs JSON to stdout.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    memory_dir = _get_arg("--memory-dir")

    if not memory_dir:
        print("Usage: find-duplicates.py --memory-dir <path>", file=sys.stderr)
        return 1

    try:
        from anamnesis.compact import find_duplicates
    except ImportError:
        print(json.dumps({"error": "anamnesis not installed"}))
        return 1

    memory_path = Path(memory_dir)
    groups = find_duplicates(memory_path)

    output = {
        "total_groups": len(groups),
        "groups": [
            {
                "files": [str(f.path) for f in g.files],
                "titles": [f.title for f in g.files],
                "similarity": round(g.similarity, 2),
            }
            for g in groups
        ],
    }

    print(json.dumps(output, indent=2))
    return 0


def _get_arg(flag: str) -> str | None:
    for i, arg in enumerate(sys.argv):
        if arg == flag and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


if __name__ == "__main__":
    sys.exit(main())
