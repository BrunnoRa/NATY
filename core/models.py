from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class AppState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    PROCESSING = "PROCESSING"
    RESEARCHING = "RESEARCHING"
    RETRIEVING = "RETRIEVING"
    GMAIL = "GMAIL"
    SPEAKING = "SPEAKING"
    ERROR = "ERROR"


class RequestType(str, Enum):
    CHAT = "CHAT"
    QUESTION = "QUESTION"
    LOCAL_ACTION = "LOCAL_ACTION"
    SEARCH = "SEARCH"
    DEEP_RESEARCH = "DEEP_RESEARCH"
    PLANNING = "PLANNING"
    TASK = "TASK"
    REMINDER = "REMINDER"
    OPEN_APP = "OPEN_APP"
    MEDIA = "MEDIA"
    OBSIDIAN_QUERY = "OBSIDIAN_QUERY"
    MEMORY = "MEMORY"
    AUTOMATION = "AUTOMATION"
    DELEGATE = "DELEGATE"
    SYSTEM = "SYSTEM"
    CONTEXT = "CONTEXT"
    CLARIFICATION = "CLARIFICATION"


@dataclass(slots=True)
class Intent:
    name: str
    entities: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    raw_text: str = ""
    request_type: str = RequestType.CLARIFICATION.value


@dataclass(slots=True)
class ToolResult:
    ok: bool
    message: str
    data: Any = None
    entity_type: str | None = None
    entity_id: int | None = None
    sources: list[dict[str, str]] = field(default_factory=list)
    type: str = "message"
    ui_hint: dict[str, Any] = field(default_factory=lambda: {"mode": "brain", "panel": "none", "title": ""})
    error: str | None = None

    def payload(self) -> dict[str, Any]:
        return {
            "success": self.ok,
            "type": self.type,
            "message": self.message,
            "data": _json_value(self.data),
            "sources": _json_value(self.sources),
            "ui": self.ui_hint,
            "error": self.error,
        }


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if is_dataclass(value):
        return _json_value(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    return str(value)


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


@dataclass(slots=True)
class ResearchSource:
    title: str
    url: str
    domain: str
    retrieved_at: str


@dataclass(slots=True)
class ResearchResult:
    query: str
    summary: str
    facts: list[str] = field(default_factory=list)
    sources: list[ResearchSource] = field(default_factory=list)
    confidence: float = 0.0


def utc_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
