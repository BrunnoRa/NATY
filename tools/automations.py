from __future__ import annotations

from datetime import datetime, timedelta

from core.models import ToolResult
from database.repositories.automations import AutomationRepository


class AutomationsTool:
    def __init__(self, repo: AutomationRepository):
        self.repo = repo

    def create(self, text: str, frequency: str, next_run: str | None) -> ToolResult:
        if not text.strip():
            return ToolResult(False, "O que a automação deve lembrar?", type="clarification", error="missing_text")
        if not next_run:
            return ToolResult(False, "Em qual dia e horário a automação deve executar?", type="clarification", error="missing_schedule")
        if frequency not in {"ONE_TIME", "DAILY", "WEEKLY"}:
            return ToolResult(False, "Esse tipo de repetição ainda não é suportado.", type="automation_error", error="unsupported_frequency")
        scheduled = datetime.fromisoformat(next_run)
        now = datetime.now().astimezone()
        if scheduled <= now and frequency == "DAILY":
            scheduled += timedelta(days=1)
            next_run = scheduled.isoformat(timespec="minutes")
        record = self.repo.create(text, frequency, next_run, {"text": text}, "notify")
        when = datetime.fromisoformat(next_run).strftime("%d/%m às %H:%M")
        repeat = {"ONE_TIME": "uma vez", "DAILY": "todos os dias", "WEEKLY": "semanalmente"}[frequency]
        return ToolResult(True, f"Automação criada: vou lembrar você {repeat}, começando em {when}.", record,
                          "automation", record["id"], type="automation_created")
