import asyncio
import json
from typing import Optional

from fastapi import WebSocket

from backend.models.events import NexusEvent


class EventBus:
    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._connections.setdefault(session_id, set()).add(ws)

    async def disconnect(self, session_id: str, ws: WebSocket):
        async with self._lock:
            if session_id in self._connections:
                self._connections[session_id].discard(ws)
                if not self._connections[session_id]:
                    del self._connections[session_id]

    async def emit(self, event: NexusEvent):
        """Broadcast a typed NexusEvent to all sockets for the session."""
        async with self._lock:
            connections = set(self._connections.get(event.session_id, set()))

        if not connections:
            return

        payload = event.model_dump_json()
        dead: set[WebSocket] = set()

        for ws in connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)

        if dead:
            async with self._lock:
                if event.session_id in self._connections:
                    self._connections[event.session_id] -= dead

    async def emit_raw(self, session_id: str, data: dict):
        """Broadcast an arbitrary dict (no schema validation)."""
        async with self._lock:
            connections = set(self._connections.get(session_id, set()))

        payload = json.dumps(data)
        for ws in connections:
            try:
                await ws.send_text(payload)
            except Exception:
                pass

    def has_listeners(self, session_id: str) -> bool:
        return bool(self._connections.get(session_id))


# Singleton
event_bus = EventBus()
