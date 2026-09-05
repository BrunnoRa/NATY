from __future__ import annotations

from datetime import date, datetime, time, timedelta
import json

from database.repositories.base import Repository


class TemporalMemoryRepository(Repository):
    def add(self, event_type: str, summary: str, *, project_id: int | None = None,
            source: str = "naty", metadata: dict | None = None,
            session_id: str | None = None, timestamp: str | None = None) -> dict:
        occurred = timestamp or datetime.now().astimezone().isoformat(timespec="seconds")
        event_id = self.db.execute(
            """INSERT INTO activity_events(timestamp,event_type,summary,project_id,source,metadata_json,session_id)
               VALUES(?,?,?,?,?,?,?)""",
            (occurred, event_type.upper(), summary.strip()[:1000], project_id, source,
             json.dumps(metadata or {}, ensure_ascii=False), session_id),
        )
        return self.get(event_id)

    def get(self, event_id: int) -> dict | None:
        row = self.db.one("SELECT * FROM activity_events WHERE id=?", (event_id,))
        return self._decode(row) if row else None

    @staticmethod
    def _decode(row) -> dict:
        item = dict(row)
        try: item["metadata"] = json.loads(item.pop("metadata_json"))
        except (json.JSONDecodeError, TypeError): item["metadata"] = {}
        return item

    def recent(self, limit: int = 6, event_type: str | None = None) -> list[dict]:
        if event_type:
            rows = self.db.query("SELECT * FROM activity_events WHERE event_type=? ORDER BY timestamp DESC,id DESC LIMIT ?",
                                 (event_type.upper(), max(1, min(limit, 50))))
        else:
            rows = self.db.query("SELECT * FROM activity_events ORDER BY timestamp DESC,id DESC LIMIT ?",
                                 (max(1, min(limit, 50)),))
        return [self._decode(row) for row in rows]

    def for_day(self, target: date) -> list[dict]:
        local = datetime.now().astimezone().tzinfo
        start = datetime.combine(target, time.min, local).isoformat(timespec="seconds")
        end = datetime.combine(target + timedelta(days=1), time.min, local).isoformat(timespec="seconds")
        rows = self.db.query("SELECT * FROM activity_events WHERE timestamp>=? AND timestamp<? ORDER BY timestamp,id", (start, end))
        return [self._decode(row) for row in rows]

    def prune(self, retention_days: int = 90, now: datetime | None = None) -> int:
        current = now or datetime.now().astimezone()
        cutoff = (current - timedelta(days=max(1, retention_days))).isoformat(timespec="seconds")
        with self.db.transaction() as connection:
            cursor = connection.execute("DELETE FROM activity_events WHERE timestamp<?", (cutoff,))
            return int(cursor.rowcount)

    def summarize_session(self, session_id: str) -> dict | None:
        rows = self.db.query("SELECT * FROM activity_events WHERE session_id=? AND event_type!='SESSION_SUMMARY' ORDER BY timestamp,id",
                             (session_id,))
        if len(rows) < 2:
            return None
        summaries = [str(row["summary"]).rstrip(".") for row in rows[-5:]]
        return self.add("SESSION_SUMMARY", "; ".join(summaries) + ".", source="session", session_id=session_id,
                        metadata={"event_count": len(rows)})
