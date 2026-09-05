from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ContextEntity:
    type: str
    id: int
    label: str = ""


class SessionContext:
    """Contexto curto; não é um histórico de conversa permanente."""

    def __init__(self, max_turns: int = 12):
        self.turns: deque[dict[str, Any]] = deque(maxlen=max_turns)
        self.active_apps: deque[dict[str, Any]] = deque(maxlen=8)
        self.last_entity: ContextEntity | None = None
        self.last_list_id: int | None = None
        self.state: dict[str, Any] = {}

    def update_active_app(self, value: dict[str, Any] | None) -> bool:
        """Keep only minimal active-window metadata for the current session."""
        if not isinstance(value, dict):
            return False
        process = str(value.get("process_name", "")).strip()[:120]
        title = str(value.get("window_title", "")).strip()[:300]
        if not process and not title:
            return False
        try:
            handle = max(0, int(value.get("window_handle", 0)))
        except (TypeError, ValueError):
            handle = 0
        item = {
            "process_name": process,
            "window_title": title,
            "timestamp": str(value.get("timestamp", ""))[:40],
            "window_handle": handle,
        }
        previous = self.active_apps[-1] if self.active_apps else None
        if previous and (previous["process_name"], previous["window_title"], previous["window_handle"]) == (
            process, title, handle
        ):
            self.active_apps[-1] = item
            return False
        self.active_apps.append(item)
        self.state["active_app"] = item
        return True

    @property
    def active_app(self) -> dict[str, Any] | None:
        return dict(self.active_apps[-1]) if self.active_apps else None

    def remember_turn(self, user: str, response: str) -> None:
        self.turns.append({"user": user, "response": response})

    def set_entity(self, entity_type: str, entity_id: int, label: str = "") -> None:
        self.last_entity = ContextEntity(entity_type, entity_id, label)
        if entity_type == "list":
            self.last_list_id = entity_id

    def clear(self) -> None:
        self.turns.clear()
        self.active_apps.clear()
        self.last_entity = None
        self.last_list_id = None
        self.state.clear()
