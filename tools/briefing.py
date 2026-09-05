from __future__ import annotations

from datetime import datetime, timedelta

from core.models import ToolResult


class BriefingTool:
    def __init__(self, db, tasks, reminders, google=None, sync_getter=None):
        self.db, self.tasks, self.reminders = db, tasks, reminders
        self.google = google
        self.sync_getter = sync_getter or (lambda: None)

    def build(self, now: datetime | None = None) -> ToolResult:
        current = now or datetime.now().astimezone()
        start = current.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        today = current.date().isoformat()
        pending = self.tasks.list("pending")
        overdue = [task for task in pending if task.get("due_at") and task["due_at"] < current.isoformat()]
        due_today = [task for task in pending if task.get("due_at") and task["due_at"][:10] == today]
        appointments = [dict(row) for row in self.db.query(
            "SELECT * FROM appointments WHERE status='scheduled' AND starts_at>=? AND starts_at<? ORDER BY starts_at",
            (start.isoformat(), end.isoformat()))]
        reminders = [item for item in self.reminders.pending() if item["remind_at"][:10] == today]
        google_events, important_mail = self._google_items(start, end)

        now_items, today_items, attention = [], [], []
        upcoming = sorted(
            [{"title": item["title"], "detail": item["starts_at"], "kind": "Compromisso"} for item in appointments] +
            [{"title": item["text"], "detail": item["remind_at"], "kind": "Lembrete"} for item in reminders] +
            google_events,
            key=lambda item: item.get("detail", ""),
        )
        if upcoming:
            item = upcoming[0]
            now_items.append({"title": item["title"], "detail": item.get("detail", ""), "kind": item.get("kind", "Agenda")})
        for task in sorted(due_today, key=lambda item: (item.get("priority") != "high", item.get("due_at") or ""))[:3]:
            today_items.append({"title": task["title"], "detail": task.get("due_at") or "Hoje", "kind": "Tarefa"})
        if not today_items and pending:
            task = pending[0]
            today_items.append({"title": task["title"], "detail": task.get("due_at") or "Sem prazo", "kind": "Próxima tarefa"})
        if overdue:
            attention.append({"title": f"{len(overdue)} tarefa(s) vencida(s)", "detail": overdue[0]["title"], "kind": "Tarefa"})
        if important_mail:
            attention.append({"title": f"{len(important_mail)} e-mail(s) importante(s)",
                              "detail": important_mail[0].get("subject", "Sem assunto"), "kind": "E-mail"})
        sync = self.sync_getter()
        if sync:
            state = sync.summary()
            if state.get("conflicts", 0):
                attention.append({"title": f"{state['conflicts']} conflito(s) de sync", "detail": "Revisão necessária", "kind": "Sync"})

        message_parts = ["Bom dia." if current.hour < 12 else "Aqui está seu briefing."]
        if due_today:
            message_parts.append(f"Você tem {len(due_today)} tarefa(s) para hoje.")
        elif pending:
            message_parts.append(f"Você tem {len(pending)} tarefa(s) pendente(s), nenhuma com prazo hoje.")
        else:
            message_parts.append("Você não tem tarefas pendentes.")
        if upcoming:
            message_parts.append(f"Seu próximo item é {upcoming[0]['title']}.")
        if attention:
            message_parts.append(f"Atenção: {attention[0]['title'].lower()}.")
        else:
            message_parts.append("Não encontrei nenhuma pendência crítica.")
        data = {"date": today, "now": now_items, "today": today_items, "attention": attention,
                "google_connected": bool(google_events or important_mail)}
        return ToolResult(True, " ".join(message_parts), data, type="daily_briefing",
                          ui_hint={"mode": "context", "panel": "briefing", "title": "Briefing do dia"})

    def _google_items(self, start: datetime, end: datetime) -> tuple[list[dict], list[dict]]:
        if not self.google or not getattr(self.google.settings, "google_enabled", False):
            return [], []
        try:
            if not self.google.auth.available():
                return [], []
            events = self.google.calendar.between(start.isoformat(), end.isoformat(), max_results=5)
            calendar = [{"title": event.get("summary", "Compromisso"),
                         "detail": (event.get("start") or {}).get("dateTime") or (event.get("start") or {}).get("date", ""),
                         "kind": "Agenda Google"} for event in events]
            mail = self.google.gmail.search("is:unread (is:important OR is:starred)", max_results=3)
            return calendar, mail
        except Exception:
            return [], []
