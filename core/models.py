from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AppState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    RESEARCHING = "RESEARCHING"
    RETRIEVING = "RETRIEVING"
    GMAIL = "GMAIL"
    SPEAKING = "SPEAKING"
    ERROR = "ERROR"


@dataclass(slots=True)
class Intent:
    name: str
    entities: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    raw_text: str = ""


@dataclass(slots=True)
class ToolResult:
    ok: bool
    message: str
    data: Any = None
    entity_type: str | None = None
    entity_id: int | None = None
    sources: list[dict[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class Task:
    id: int
    title: str
    description: str = ""
    project_id: int | None = None
    status: str = "pending"
    priority: str = "normal"
    created_at: str = ""
    due_at: str | None = None
    estimated_minutes: int | None = None
    completed_at: str | None = None
    postpone_count: int = 0
    last_prompted_at: str | None = None


@dataclass(slots=True)
class ResearchItem:
    title: str
    url: str
    snippet: str = ""
    relevant_text: str = ""
    price: float | None = None
    source: str = ""
    observed_at: str = ""


def utc_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
