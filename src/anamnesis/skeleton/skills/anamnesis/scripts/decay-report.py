#!/usr/bin/env python3
"""Report stale memories that haven't been accessed recently.

Usage: python3 decay-report.py --memory-dir <path> [--days N]

Outputs JSON to stdout.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    memory_dir = _get_arg("--memory-dir")
    days = int(_get_arg("--days") or "90")

    if not memory_dir:
        print("Usage: decay-report.py --memory-dir <path> [--days N]", file=sys.stderr)
        return 1

    try:
        from anamnesis.decay import decay_report
    except ImportError:
        print(json.dumps({"error": "anamnesis not installed"}))
        return 1

    memory_path = Path(memory_dir)
    result = decay_report(memory_path, threshold_days=days)

    output = {
        "threshold_days": days,
        "total_stale": len(result.stale),
        "stale": [
            {
                "file": str(m.path),
                "title": m.title,
                "days_stale": m.days_stale,
                "importance": m.importance,
                "last_accessed": m.last_accessed.isoformat(),
            }
            for m in result.stale
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
