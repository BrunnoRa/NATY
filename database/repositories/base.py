from __future__ import annotations

from database.connection import Database


class Repository:
    def __init__(self, db: Database):
        self.db = db

    def activity(self, action: str, entity_type: str, entity_id: int | None, summary: str) -> None:
        self.db.execute(
            "INSERT INTO activity_history(action, entity_type, entity_id, summary) VALUES (?, ?, ?, ?)",
            (action, entity_type, entity_id, summary),
        )
