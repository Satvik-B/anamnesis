#!/usr/bin/env python3
"""Mark a Claude Code session as processed in the ledger.

Usage: python3 mark-processed.py --memory-dir <path> --session-id <id> [--memories-created N]

Outputs JSON to stdout.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    memory_dir = _get_arg("--memory-dir")
    session_id = _get_arg("--session-id")
    memories_created = int(_get_arg("--memories-created") or "0")

    if not memory_dir or not session_id:
        print("Usage: mark-processed.py --memory-dir <path> --session-id <id> [--memories-created N]", file=sys.stderr)
        return 1

    try:
        from anamnesis.ledger import Ledger
    except ImportError:
        print(json.dumps({"error": "anamnesis not installed"}))
        return 1

    memory_path = Path(memory_dir)
    ledger = Ledger.load(memory_path)
    ledger.mark_processed(session_id, memories_created=memories_created)
    ledger.save()

    print(json.dumps({
        "status": "ok",
        "session_id": session_id,
        "memories_created": memories_created,
    }))
    return 0


def _get_arg(flag: str) -> str | None:
    for i, arg in enumerate(sys.argv):
        if arg == flag and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


if __name__ == "__main__":
    sys.exit(main())
