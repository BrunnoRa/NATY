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
        self.last_entity: ContextEntity | None = None
        self.last_list_id: int | None = None
        self.state: dict[str, Any] = {}

    def remember_turn(self, user: str, response: str) -> None:
        self.turns.append({"user": user, "response": response})

    def set_entity(self, entity_type: str, entity_id: int, label: str = "") -> None:
        self.last_entity = ContextEntity(entity_type, entity_id, label)
        if entity_type == "list":
            self.last_list_id = entity_id

    def clear(self) -> None:
        self.turns.clear()
        self.last_entity = None
        self.last_list_id = None
        self.state.clear()
