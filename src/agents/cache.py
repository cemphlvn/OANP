"""
Session persistence and checkpointing.

Best practices from LangGraph's persistence layer:
1. Checkpoint after every round (not just at the end)
2. Thread-based: each session is a thread with ordered checkpoints
3. Enables: resume from crash, replay any point, time-travel debug
4. Stores to disk (JSON files) for durability — Redis/Postgres for production

Current approach: simple JSON file persistence per session.
Production upgrade path: LangGraph InMemorySaver → PostgresSaver.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import logging

from ..protocol.types import NegotiationState

logger = logging.getLogger(__name__)


class SessionStore:
    """Persistent session storage with per-round checkpointing."""

    def __init__(self, data_dir: str = "results"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        # In-memory cache for fast access
        self._cache: dict[str, NegotiationState] = {}

    def save(self, state: NegotiationState) -> None:
        """Save current state as a checkpoint — full state for reload."""
        self._cache[state.id] = state

        # Persist full state to disk (Pydantic model_dump handles all nested types)
        path = self.data_dir / f"{state.id}.json"
        try:
            data = state.model_dump(mode="json")
            data["_checkpoint_at"] = datetime.now(tz=timezone.utc).isoformat()
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error("Save failed for %s: %s", state.id, e)

    def get(self, session_id: str) -> Optional[NegotiationState]:
        """Get session from cache, falling back to disk."""
        if session_id in self._cache:
            return self._cache[session_id]

        # Try loading from disk
        path = self.data_dir / f"{session_id}.json"
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                # Remove our internal metadata before parsing
                data.pop("_checkpoint_at", None)
                state = NegotiationState.model_validate(data)
                self._cache[session_id] = state
                logger.debug("Loaded %s from disk", session_id)
                return state
            except Exception as e:
                logger.error("Failed to load %s: %s", session_id, e)

        return None

    def put(self, state: NegotiationState) -> None:
        """Put state in cache without persisting to disk."""
        self._cache[state.id] = state

    def list_sessions(self) -> list[dict]:
        """List all sessions (from cache + disk)."""
        sessions = []

        # From cache (live sessions)
        for sid, state in self._cache.items():
            sessions.append({
                "session_id": sid,
                "phase": state.protocol.phase.value,
                "outcome": state.outcome,
                "total_moves": state.protocol.total_moves,
                "parties": [p.name for p in state.parties],
            })

        # From disk (completed sessions not in cache)
        for path in self.data_dir.glob("neg_*.json"):
            sid = path.stem
            if sid not in self._cache:
                try:
                    with open(path) as f:
                        data = json.load(f)
                    sessions.append({
                        "session_id": sid,
                        "phase": data.get("phase", "?"),
                        "outcome": data.get("outcome"),
                        "total_moves": data.get("total_moves", 0),
                        "parties": [p.get("name", "?") for p in data.get("parties", [])],
                    })
                except Exception:
                    pass

        return sessions

    @property
    def count(self) -> int:
        """Total sessions (cache + disk)."""
        disk_count = len(list(self.data_dir.glob("neg_*.json")))
        cache_only = len([k for k in self._cache if not (self.data_dir / f"{k}.json").exists()])
        return disk_count + cache_only
