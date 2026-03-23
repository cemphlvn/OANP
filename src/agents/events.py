"""
EventBus — decoupled event system for negotiation streaming.

Replaces the fragile callback pattern with a proper pub/sub bus.
Multiple listeners can subscribe (WebSocket, file logger, metrics tracker).
Event history enables replay mode.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Awaitable, Callable

EventListener = Callable[[str, dict], Awaitable[None] | None]


class EventBus:
    """Async event bus with history for negotiation event streaming."""

    def __init__(self):
        self._listeners: list[EventListener] = []
        self._history: list[dict] = []

    def subscribe(self, listener: EventListener) -> Callable[[], None]:
        """Subscribe a listener. Returns an unsubscribe function."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    async def emit(self, event_type: str, data: dict) -> None:
        """Emit an event to all listeners and record in history."""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }
        self._history.append(event)

        for listener in self._listeners:
            try:
                result = listener(event_type, data)
                if asyncio.iscoroutine(result) or asyncio.isfuture(result):
                    await result
            except Exception:
                import logging
                logging.getLogger(__name__).exception("Listener failed for %s", event_type)

    @property
    def history(self) -> list[dict]:
        """Full event history — enables replay mode."""
        return list(self._history)

    @property
    def move_count(self) -> int:
        return sum(1 for e in self._history if e["type"] in ("move", "mediator_note"))

    def clear(self) -> None:
        self._history.clear()
