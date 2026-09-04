from __future__ import annotations

from database.repositories.base import Repository


class ProjectRepository(Repository):
    def create(self, name: str, description: str = "") -> dict:
        project_id = self.db.execute("INSERT INTO projects(name, description) VALUES (?, ?)", (name.strip(), description.strip()))
        self.activity("created", "project", project_id, name)
        return self.get(project_id)

    def get(self, project_id: int) -> dict | None:
        row = self.db.one("SELECT * FROM projects WHERE id = ?", (project_id,))
        return dict(row) if row else None

    def find(self, name: str) -> dict | None:
        row = self.db.one("SELECT * FROM projects WHERE name = ? COLLATE NOCASE", (name.strip(),))
        return dict(row) if row else None

    def list(self, status: str | None = "active") -> list[dict]:
        rows = self.db.query("SELECT * FROM projects WHERE status = ? ORDER BY name" if status else "SELECT * FROM projects ORDER BY name", (status,) if status else ())
        return [dict(r) for r in rows]

    def tasks(self, project_id: int, status: str | None = "pending") -> list[dict]:
        sql = "SELECT * FROM tasks WHERE project_id = ?"
        params: tuple = (project_id,)
        if status:
            sql += " AND status = ?"
            params += (status,)
        return [dict(r) for r in self.db.query(sql + " ORDER BY due_at IS NULL, due_at", params)]
