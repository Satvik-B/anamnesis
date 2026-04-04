"""Session ledger — tracks which Claude Code sessions have been processed."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

LEDGER_FILENAME = ".sessions-ledger.yaml"


@dataclass
class SessionEntry:
    """A single processed-session record."""

    session_id: str
    processed_date: str  # ISO format YYYY-MM-DD
    memories_created: int = 0
    content_hash: str = ""


@dataclass
class Ledger:
    """Persistent registry of processed sessions."""

    entries: dict[str, SessionEntry] = field(default_factory=dict)
    _path: Path | None = field(default=None, repr=False)

    @classmethod
    def load(cls, memory_dir: Path) -> Ledger:
        """Load ledger from *memory_dir*/.sessions-ledger.yaml.  Create empty if missing."""
        path = memory_dir / LEDGER_FILENAME
        if not path.exists():
            return cls(_path=path)

        with open(path) as f:
            raw = yaml.safe_load(f) or {}

        entries: dict[str, SessionEntry] = {}
        for sid, data in raw.get("sessions", {}).items():
            entries[sid] = SessionEntry(
                session_id=sid,
                processed_date=data.get("processed_date", ""),
                memories_created=data.get("memories_created", 0),
                content_hash=data.get("content_hash", ""),
            )
        return cls(entries=entries, _path=path)

    def save(self) -> None:
        """Write ledger back to disk."""
        if self._path is None:
            raise ValueError("Ledger has no path — load() first")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, dict[str, object]] = {}
        for sid, entry in self.entries.items():
            data[sid] = {
                "processed_date": entry.processed_date,
                "memories_created": entry.memories_created,
                "content_hash": entry.content_hash,
            }
        with open(self._path, "w") as f:
            yaml.dump({"sessions": data}, f, default_flow_style=False, sort_keys=False)

    def mark_processed(
        self,
        session_id: str,
        memories_created: int = 0,
        content_hash: str = "",
    ) -> None:
        """Record that a session has been processed (or update an existing entry)."""
        self.entries[session_id] = SessionEntry(
            session_id=session_id,
            processed_date=datetime.now().strftime("%Y-%m-%d"),
            memories_created=memories_created,
            content_hash=content_hash,
        )

    def is_processed(self, session_id: str) -> bool:
        """Return True if *session_id* has already been processed."""
        return session_id in self.entries

    def needs_reprocessing(self, session_id: str, current_hash: str) -> bool:
        """Return True if the session's content hash differs from what was recorded."""
        entry = self.entries.get(session_id)
        if entry is None:
            return True
        return entry.content_hash != current_hash

    def get_stats(self) -> dict[str, object]:
        """Return summary statistics about processed sessions."""
        if not self.entries:
            return {"total_processed": 0, "total_memories": 0, "oldest": None, "newest": None}
        dates = [e.processed_date for e in self.entries.values()]
        return {
            "total_processed": len(self.entries),
            "total_memories": sum(e.memories_created for e in self.entries.values()),
            "oldest": min(dates),
            "newest": max(dates),
        }
