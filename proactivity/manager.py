from __future__ import annotations

from datetime import datetime, time, timedelta


class ProactivityManager:
    def __init__(self, settings, db, tasks, reminders, notifications, emit, sync_getter=None):
        self.settings, self.db, self.tasks, self.reminders = settings, db, tasks, reminders
        self.notifications, self.emit = notifications, emit
        self.sync_getter = sync_getter or (lambda: None)

    @staticmethod
    def _clock(value: str, fallback: time) -> time:
        try:
            hour, minute = (int(part) for part in value.split(":", 1))
            return time(hour, minute)
        except (ValueError, TypeError):
            return fallback

    def in_quiet_hours(self, now: datetime) -> bool:
        if not getattr(self.settings, "quiet_hours_enabled", False):
            return False
        start = self._clock(getattr(self.settings, "quiet_hours_start", "22:00"), time(22, 0))
        end = self._clock(getattr(self.settings, "quiet_hours_end", "07:00"), time(7, 0))
        current = now.timetz().replace(tzinfo=None)
        return start <= current < end if start < end else current >= start or current < end

    def consider(self, event_key: str, category: str, priority: str, title: str, message: str,
                 *, now: datetime | None = None, cooldown_minutes: int = 1440, action: dict | None = None) -> bool:
        current = now or datetime.now().astimezone()
        level = str(getattr(self.settings, "proactivity_level", "important")).casefold()
        priority = priority.upper()
        if level == "off" or (priority == "INFO" and level != "assistant"):
            return False
        if self.in_quiet_hours(current) and priority != "URGENT":
            return False
        previous = self.db.one("SELECT last_shown,cooldown_minutes FROM proactivity_events WHERE event_key=?", (event_key,))
        if previous:
            try:
                last = datetime.fromisoformat(previous["last_shown"])
                if current < last + timedelta(minutes=int(previous["cooldown_minutes"])):
                    return False
            except (ValueError, TypeError):
                pass
        stamp = current.isoformat(timespec="seconds")
        self.notifications.add(category, priority, title, message, action=action, event_key=event_key, timestamp=stamp)
        self.db.execute("""INSERT INTO proactivity_events(event_key,last_shown,cooldown_minutes) VALUES(?,?,?)
                           ON CONFLICT(event_key) DO UPDATE SET last_shown=excluded.last_shown,cooldown_minutes=excluded.cooldown_minutes""",
                        (event_key, stamp, cooldown_minutes))
        self.emit(title, message)
        return True

    def scan(self, now: datetime | None = None) -> int:
        current = now or datetime.now().astimezone()
        emitted = 0
        for task in self.tasks.list("pending", current.isoformat(timespec="seconds")):
            emitted += self.consider(f"task-overdue:{task['id']}", "TASK", "IMPORTANT", "Tarefa vencida",
                                     f"'{task['title']}' está vencida.", now=current, cooldown_minutes=1440)
        soon = (current + timedelta(minutes=30)).isoformat(timespec="seconds")
        for reminder in self.reminders.due(soon):
            if reminder["remind_at"] >= current.isoformat(timespec="seconds"):
                emitted += self.consider(f"reminder-soon:{reminder['id']}", "REMINDER", "IMPORTANT", "Lembrete próximo",
                                         reminder["text"], now=current, cooldown_minutes=60)
        sync = self.sync_getter()
        if sync:
            state = sync.summary()
            if state.get("conflicts", 0):
                emitted += self.consider("sync-conflicts", "SYNC", "IMPORTANT", "Conflito de sincronização",
                                         f"Há {state['conflicts']} conflito(s) para revisar.", now=current, cooldown_minutes=60)
        if str(getattr(self.settings, "proactivity_level", "important")).casefold() == "assistant":
            emitted += self.consider(f"briefing-suggestion:{current.date()}", "NATY", "INFO", "Briefing disponível",
                                     "Peça 'Naty, como está meu dia?' quando quiser.", now=current, cooldown_minutes=1440)
        return emitted
