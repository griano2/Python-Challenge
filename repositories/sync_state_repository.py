"""
Persists the last successful sync timestamp per pair in config/sync_state.json.

Schema:
{
  "<pair_name>": {
    "last_synced_at": "2026-09-07T13:30:00.000000+00:00"
  }
}
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional


class SyncStateRepository:

    def __init__(self, state_file: str = "config/sync_state.json"):
        self.state_file = state_file

    # ── Private helpers ──────────────────────────────────────────────────────

    def _load(self) -> dict:
        if not os.path.exists(self.state_file):
            return {}
        with open(self.state_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, state: dict) -> None:
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    # ── Public API ───────────────────────────────────────────────────────────

    def get_last_synced(self, pair_name: str) -> Optional[datetime]:
        """Return the UTC datetime of the last successful sync, or None."""
        state = self._load()
        entry = state.get(pair_name)
        if not entry or "last_synced_at" not in entry:
            return None
        return datetime.fromisoformat(entry["last_synced_at"])

    def mark_synced(self, pair_name: str) -> None:
        """Record the current UTC time as the last successful sync for pair_name."""
        state = self._load()
        state[pair_name] = {
            "last_synced_at": datetime.now(tz=timezone.utc).isoformat()
        }
        self._save(state)
