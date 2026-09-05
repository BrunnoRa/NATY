from __future__ import annotations

from datetime import datetime
import json

from database.repositories.base import Repository


class NotificationRepository(Repository):
    @staticmethod
    def _decode(row) -> dict:
        item = dict(row)
        try: item["action"] = json.loads(item.pop("action_json") or "{}")
        except (json.JSONDecodeError, TypeError): item["action"] = {}
        item["read"] = bool(item["read"])
        return item

    def add(self, category: str, priority: str, title: str, message: str, *,
            action: dict | None = None, event_key: str | None = None,
            timestamp: str | None = None) -> dict:
        notification_id = self.db.execute(
            """INSERT INTO notification_items(timestamp,category,priority,title,message,action_json,event_key)
               VALUES(?,?,?,?,?,?,?)""",
            (timestamp or datetime.now().astimezone().isoformat(timespec="seconds"), category.upper(), priority.upper(),
             title.strip()[:160], message.strip()[:1000], json.dumps(action or {}, ensure_ascii=False), event_key),
        )
        return self.get(notification_id)

    def get(self, notification_id: int) -> dict | None:
        row = self.db.one("SELECT * FROM notification_items WHERE id=?", (notification_id,))
        return self._decode(row) if row else None

    def list(self, *, unread_only: bool = False, priorities: tuple[str, ...] = (), limit: int = 30) -> list[dict]:
        clauses, params = [], []
        if unread_only: clauses.append("read=0")
        if priorities:
            clauses.append("priority IN (" + ",".join("?" for _ in priorities) + ")")
            params.extend(value.upper() for value in priorities)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self.db.query(f"SELECT * FROM notification_items{where} ORDER BY timestamp DESC,id DESC LIMIT ?",
                             (*params, max(1, min(limit, 100))))
        return [self._decode(row) for row in rows]

    def mark_read(self, notification_id: int | None = None) -> int:
        with self.db.transaction() as connection:
            cursor = (connection.execute("UPDATE notification_items SET read=1 WHERE id=?", (notification_id,))
                      if notification_id else connection.execute("UPDATE notification_items SET read=1 WHERE read=0"))
            return int(cursor.rowcount)
