from datetime import datetime
from database.repositories.base import Repository


class ReminderRepository(Repository):
    def create(self, text: str, remind_at: str) -> dict:
        reminder_id = self.db.execute("INSERT INTO reminders(text, remind_at) VALUES (?, ?)", (text.strip(), remind_at))
        self.activity("created", "reminder", reminder_id, text)
        return self.get(reminder_id)

    def get(self, reminder_id: int) -> dict | None:
        row = self.db.one("SELECT * FROM reminders WHERE id = ?", (reminder_id,))
        return dict(row) if row else None

    def pending(self) -> list[dict]:
        return [dict(r) for r in self.db.query("SELECT * FROM reminders WHERE status = 'pending' ORDER BY remind_at")]

    def due(self, now: str | None = None) -> list[dict]:
        now = now or datetime.now().astimezone().isoformat(timespec="seconds")
        return [dict(r) for r in self.db.query("SELECT * FROM reminders WHERE status = 'pending' AND remind_at <= ? ORDER BY remind_at", (now,))]

    def mark_triggered(self, reminder_id: int) -> None:
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        self.db.execute("UPDATE reminders SET status = 'triggered', triggered_at = ?, last_prompted_at = ? WHERE id = ?", (now, now, reminder_id))
