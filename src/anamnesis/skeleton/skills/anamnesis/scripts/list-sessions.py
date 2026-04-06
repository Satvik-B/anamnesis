#!/usr/bin/env python3
"""List Claude Code sessions and their sync status.

Usage: python3 list-sessions.py --sessions-dir <path> --memory-dir <path>

Outputs JSON to stdout.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    sessions_dir = _get_arg("--sessions-dir")
    memory_dir = _get_arg("--memory-dir")

    if not sessions_dir or not memory_dir:
        print("Usage: list-sessions.py --sessions-dir <path> --memory-dir <path>", file=sys.stderr)
        return 1

    sessions_path = Path(sessions_dir)
    memory_path = Path(memory_dir)

    if not sessions_path.exists():
        print(json.dumps({"error": f"Sessions dir not found: {sessions_dir}", "total": 0, "processed": 0, "unprocessed": []}))
        return 0

    try:
        from anamnesis.ledger import Ledger
    except ImportError:
        print(json.dumps({"error": "anamnesis not installed. Run: pip install anamnesis"}))
        return 1

    # List all JSONL session files
    all_sessions = sorted(sessions_path.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)

    # Load ledger to check processed status
    ledger = Ledger.load(memory_path)

    unprocessed = []
    for f in all_sessions:
        if not ledger.is_processed(f.stem):
            unprocessed.append({
                "id": f.stem,
                "path": str(f),
                "size_kb": round(f.stat().st_size / 1024, 1),
            })

    result = {
        "sessions_dir": str(sessions_path),
        "memory_dir": str(memory_path),
        "total": len(all_sessions),
        "processed": len(all_sessions) - len(unprocessed),
        "unprocessed": unprocessed,
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
