from __future__ import annotations

from datetime import datetime, timedelta
import json

from database.repositories.base import Repository


class AutomationRepository(Repository):
    def create(self, name: str, frequency: str, next_run_at: str, payload: dict, action_type: str = "notify") -> dict:
        automation_id = self.db.execute(
            """INSERT INTO automation_rules(name, trigger_type, trigger_value, action_type, payload_json, next_run_at)
               VALUES (?, 'time', ?, ?, ?, ?)""",
            (name.strip(), frequency, action_type, json.dumps(payload, ensure_ascii=False), next_run_at),
        )
        return self.get(automation_id)

    def get(self, automation_id: int) -> dict | None:
        row = self.db.one("SELECT * FROM automation_rules WHERE id=?", (automation_id,))
        if not row:
            return None
        result = dict(row)
        result["payload"] = json.loads(result.pop("payload_json") or "{}")
        return result

    def list(self, enabled_only: bool = True) -> list[dict]:
        where = " WHERE enabled=1" if enabled_only else ""
        return [self.get(row["id"]) for row in self.db.query(f"SELECT id FROM automation_rules{where} ORDER BY next_run_at, id")]

    def due(self, now: str) -> list[dict]:
        return [self.get(row["id"]) for row in self.db.query(
            "SELECT id FROM automation_rules WHERE enabled=1 AND next_run_at IS NOT NULL AND next_run_at<=? ORDER BY next_run_at", (now,)
        )]

    def mark_run(self, automation_id: int, frequency: str, ran_at: str) -> None:
        current = datetime.fromisoformat(ran_at)
        if frequency == "DAILY":
            next_run = current + timedelta(days=1)
        elif frequency == "WEEKLY":
            next_run = current + timedelta(days=7)
        else:
            self.db.execute("UPDATE automation_rules SET enabled=0, last_run_at=? WHERE id=?", (ran_at, automation_id))
            return
        self.db.execute(
            "UPDATE automation_rules SET last_run_at=?, next_run_at=? WHERE id=?",
            (ran_at, next_run.isoformat(timespec="minutes"), automation_id),
        )
