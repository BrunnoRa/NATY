from __future__ import annotations

from datetime import datetime, timedelta
import threading
from collections.abc import Callable

from database.repositories.reminders import ReminderRepository
from database.repositories.tasks import TaskRepository


class Scheduler:
    def __init__(self, reminders: ReminderRepository, tasks: TaskRepository, notify: Callable[[str, str], None], interval: int = 30, settings=None, automations=None, proactivity=None):
        self.reminders, self.tasks, self.notify = reminders, tasks, notify
        self.settings = settings
        self.automations = automations
        self.proactivity = proactivity
        self.interval = max(15, interval)
        self._stop = threading.Event(); self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive(): return
        self._stop.clear(); self._thread = threading.Thread(target=self._run, name="NatyScheduler", daemon=True); self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive(): self._thread.join(timeout=2)

    def check_once(self) -> None:
        now = datetime.now().astimezone()
        for reminder in self.reminders.due(now.isoformat(timespec="seconds")):
            self.notify("Lembrete da Naty", reminder["text"])
            self.reminders.mark_triggered(reminder["id"])
        if self.automations:
            for automation in self.automations.due(now.isoformat(timespec="minutes")):
                payload = automation.get("payload", {})
                if automation["action_type"] in {"notify", "reminder"}:
                    self.notify("Automação da Naty", payload.get("text") or automation["name"])
                self.automations.mark_run(automation["id"], automation["trigger_value"], now.isoformat(timespec="minutes"))
        proactivity = self.settings is None or self.settings.proactivity_enabled
        followup = self.settings is None or self.settings.overdue_followup
        if proactivity and followup and self.proactivity is None:
            cutoff = (now - timedelta(hours=24)).isoformat(timespec="seconds")
            for task in self.tasks.list("pending", now.isoformat(timespec="seconds")):
                if not task["last_prompted_at"] or task["last_prompted_at"] < cutoff:
                    self.notify("Tarefa pendente", f"Você ainda não concluiu '{task['title']}'.")
                    self.tasks.update(task["id"], last_prompted_at=now.isoformat(timespec="seconds"))
        if self.settings and proactivity:
            if getattr(self.settings, "daily_briefing_enabled", False):
                self._briefing_ready(now, getattr(self.settings, "daily_briefing_time", "08:00"))
            if self.settings.morning_briefing:
                self._daily_summary(now, "morning", self.settings.morning_briefing_time, "Bom dia")
            if self.settings.evening_review:
                self._daily_summary(now, "evening", self.settings.evening_review_time, "Revisão do dia")
        if self.proactivity:
            self.proactivity.scan(now)

    def _daily_summary(self, now: datetime, kind: str, configured_time: str, title: str) -> None:
        try:
            hour, minute = (int(value) for value in configured_time.split(":", 1))
        except (ValueError, AttributeError):
            return
        if (now.hour, now.minute) < (hour, minute):
            return
        key = f"proactivity:{kind}:{now.date().isoformat()}"
        if self.tasks.db.one("SELECT 1 FROM preferences WHERE key=?", (key,)):
            return
        pending = self.tasks.list("pending")
        due = [task for task in pending if task.get("due_at") and task["due_at"][:10] <= now.date().isoformat()]
        message = f"Você tem {len(pending)} tarefa(s) pendente(s)"
        if due:
            message += f", {len(due)} com prazo até hoje"
        message += "."
        self.notify(title, message)
        self.tasks.db.execute("INSERT INTO preferences(key,value) VALUES(?,?)", (key, now.isoformat(timespec="seconds")))

    def _briefing_ready(self, now: datetime, configured_time: str) -> None:
        try:
            hour, minute = (int(value) for value in configured_time.split(":", 1))
        except (ValueError, AttributeError):
            return
        if (now.hour, now.minute) < (hour, minute):
            return
        key = f"daily_briefing:{now.date().isoformat()}"
        if self.tasks.db.one("SELECT 1 FROM preferences WHERE key=?", (key,)):
            return
        self.notify("NATY", "Seu briefing está pronto.")
        self.tasks.db.execute("INSERT INTO preferences(key,value) VALUES(?,?)", (key, now.isoformat(timespec="seconds")))

    def _run(self) -> None:
        while not self._stop.is_set():
            try: self.check_once()
            except Exception: pass
            self._stop.wait(self.interval)
