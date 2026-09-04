from core.models import ToolResult
from database.connection import Database


class CalendarTool:
    def __init__(self, db: Database): self.db = db

    def create(self, title: str, starts_at: str, ends_at: str | None = None, location: str | None = None) -> ToolResult:
        if not starts_at: return ToolResult(False, "Para quando é o compromisso?")
        item_id = self.db.execute("INSERT INTO appointments(title, starts_at, ends_at, location) VALUES (?, ?, ?, ?)", (title, starts_at, ends_at, location))
        return ToolResult(True, f"Compromisso '{title}' criado.", {"id": item_id, "starts_at": starts_at}, "appointment", item_id)

    def today(self) -> ToolResult:
        from datetime import datetime, timedelta
        now = datetime.now().astimezone(); start = now.replace(hour=0, minute=0, second=0, microsecond=0); end = start + timedelta(days=1)
        rows = [dict(r) for r in self.db.query("SELECT * FROM appointments WHERE status='scheduled' AND starts_at >= ? AND starts_at < ? ORDER BY starts_at", (start.isoformat(), end.isoformat()))]
        if not rows: return ToolResult(True, "Você não tem compromissos hoje.", [])
        return ToolResult(True, "Compromissos de hoje: " + "; ".join(r["title"] for r in rows) + ".", rows)
