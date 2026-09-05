from __future__ import annotations

from datetime import datetime, timedelta

from core.models import ToolResult


class PlanningTool:
    def __init__(self, db, tasks, reminders):
        self.db, self.tasks, self.reminders = db, tasks, reminders

    def show_day(self, day: str) -> ToolResult:
        now = datetime.now().astimezone()
        target = now.date() + (timedelta(days=1) if day == "tomorrow" else timedelta())
        start = datetime.combine(target, datetime.min.time(), tzinfo=now.tzinfo)
        end = start + timedelta(days=1)
        params = (start.isoformat(), end.isoformat())
        tasks = [dict(row) for row in self.db.query(
            "SELECT * FROM tasks WHERE status='pending' AND due_at>=? AND due_at<? ORDER BY priority='high' DESC, due_at", params)]
        appointments = [dict(row) for row in self.db.query(
            "SELECT * FROM appointments WHERE status='scheduled' AND starts_at>=? AND starts_at<? ORDER BY starts_at", params)]
        reminders = [dict(row) for row in self.db.query(
            "SELECT * FROM reminders WHERE status='pending' AND remind_at>=? AND remind_at<? ORDER BY remind_at", params)]
        label = "amanhã" if day == "tomorrow" else "hoje"
        total = len(tasks) + len(appointments) + len(reminders)
        if total == 0:
            message = f"Você não tem tarefas, compromissos ou lembretes para {label}."
        else:
            message = f"Para {label}: {len(tasks)} tarefa(s), {len(appointments)} compromisso(s) e {len(reminders)} lembrete(s)."
        return ToolResult(True, message, {"date": target.isoformat(), "tasks": tasks, "appointments": appointments, "reminders": reminders}, type="day_summary")

    def next_task(self) -> ToolResult:
        result = self.tasks.list_pending()
        tasks = result.data or []
        if not tasks:
            return ToolResult(True, "Você não tem uma próxima tarefa pendente.", [], type="next_task")
        task = tasks[0]
        return ToolResult(True, f"Sua próxima tarefa é '{task['title']}'.", task, "task", task["id"], type="next_task")
