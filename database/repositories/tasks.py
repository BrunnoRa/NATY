from __future__ import annotations

from datetime import datetime
from database.repositories.base import Repository


class TaskRepository(Repository):
    def create(self, title: str, due_at: str | None = None, project_id: int | None = None,
               priority: str = "normal", estimated_minutes: int | None = None, description: str = "") -> dict:
        task_id = self.db.execute(
            """INSERT INTO tasks(title, description, project_id, priority, due_at, estimated_minutes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (title.strip(), description.strip(), project_id, priority, due_at, estimated_minutes),
        )
        self.activity("created", "task", task_id, title)
        return self.get(task_id)

    def get(self, task_id: int) -> dict | None:
        row = self.db.one("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return dict(row) if row else None

    def list(self, status: str | None = "pending", due_before: str | None = None) -> list[dict]:
        clauses, params = [], []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if due_before:
            clauses.append("due_at IS NOT NULL AND due_at <= ?")
            params.append(due_before)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self.db.query(
            f"SELECT * FROM tasks{where} ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END, due_at IS NULL, due_at, id",
            tuple(params),
        )
        return [dict(r) for r in rows]

    def update(self, task_id: int, **changes) -> dict | None:
        allowed = {"title", "description", "project_id", "status", "priority", "due_at", "estimated_minutes", "completed_at", "postpone_count", "last_prompted_at"}
        filtered = {k: v for k, v in changes.items() if k in allowed}
        if not filtered:
            return self.get(task_id)
        sql = ", ".join(f"{key} = ?" for key in filtered)
        self.db.execute(f"UPDATE tasks SET {sql} WHERE id = ?", (*filtered.values(), task_id))
        self.activity("updated", "task", task_id, ", ".join(filtered))
        return self.get(task_id)

    def complete(self, task_id: int) -> dict | None:
        return self.update(task_id, status="completed", completed_at=datetime.now().astimezone().isoformat(timespec="seconds"))

    def postpone(self, task_id: int, due_at: str) -> dict | None:
        task = self.get(task_id)
        if not task:
            return None
        return self.update(task_id, due_at=due_at, postpone_count=int(task["postpone_count"]) + 1, status="pending")

    def delete_all(self) -> int:
        with self.db.transaction() as conn:
            count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            conn.execute("DELETE FROM tasks")
        return int(count)
