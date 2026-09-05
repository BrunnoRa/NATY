from __future__ import annotations

from datetime import date, timedelta

from core.models import ToolResult


class TemporalMemoryTool:
    def __init__(self, repository): self.repository = repository

    def recall(self, kind: str = "where_stopped") -> ToolResult:
        if kind == "today":
            events = self.repository.for_day(date.today())
            prefix = "Hoje"
        elif kind == "yesterday":
            events = self.repository.for_day(date.today() - timedelta(days=1))
            prefix = "Ontem"
        elif kind == "last_research":
            events = self.repository.recent(1, "RESEARCH")
            prefix = "Sua última pesquisa"
        elif kind == "last_decision":
            events = self.repository.recent(1, "DECISION")
            prefix = "Sua última decisão"
        else:
            events = self.repository.recent(6)
            prefix = "Onde paramos"
        if not events:
            return ToolResult(True, "Ainda não tenho atividade útil registrada para esse período.", {"events": []},
                              type="temporal_context", ui_hint={"mode": "context", "panel": "timeline", "title": prefix})
        ordered = events if kind in {"today", "yesterday"} else list(reversed(events))
        preview = ordered[-4:]
        message = f"{prefix}: " + " ".join(f"{item['summary'].rstrip('.')}." for item in preview)
        return ToolResult(True, message, {"events": ordered}, type="temporal_context",
                          ui_hint={"mode": "context", "panel": "timeline", "title": prefix})
