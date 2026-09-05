from __future__ import annotations

import json
import unicodedata

from database.repositories.base import Repository


def normalized(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFD", value.casefold().strip())
                   if unicodedata.category(char) != "Mn")


class WorkspaceRepository(Repository):
    @staticmethod
    def _decode(row) -> dict:
        item = dict(row)
        for source, target in (("aliases_json", "aliases"), ("actions_json", "actions")):
            try: item[target] = json.loads(item.pop(source) or "[]")
            except (json.JSONDecodeError, TypeError): item[target] = []
        item["enabled"], item["active"] = bool(item["enabled"]), bool(item["active"])
        return item

    def get(self, workspace_id: int) -> dict | None:
        row = self.db.one("SELECT * FROM workspaces WHERE id=?", (workspace_id,))
        return self._decode(row) if row else None

    def find(self, name_or_alias: str) -> dict | None:
        wanted = normalized(name_or_alias)
        for workspace in self.list(enabled_only=False):
            names = [workspace["name"], *workspace["aliases"]]
            if wanted in {normalized(name) for name in names}:
                return workspace
        return None

    def list(self, enabled_only: bool = True) -> list[dict]:
        where = " WHERE enabled=1" if enabled_only else ""
        return [self._decode(row) for row in self.db.query(f"SELECT * FROM workspaces{where} ORDER BY name")]

    def save(self, name: str, *, workspace_id: int | None = None, aliases: list[str] | None = None,
             actions: list[dict] | None = None, project_id: int | None = None,
             focus_minutes: int | None = None, enabled: bool = True) -> dict:
        clean_name = name.strip()[:80]
        if not clean_name:
            raise ValueError("O modo precisa de um nome.")
        aliases = [str(value).strip()[:80] for value in (aliases or []) if str(value).strip()]
        actions = list(actions or [])
        if workspace_id:
            self.db.execute("""UPDATE workspaces SET name=?,aliases_json=?,actions_json=?,project_id=?,focus_minutes=?,enabled=?,updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                            (clean_name, json.dumps(aliases, ensure_ascii=False), json.dumps(actions, ensure_ascii=False),
                             project_id, focus_minutes, int(enabled), workspace_id))
            return self.get(workspace_id)
        existing = self.find(clean_name)
        if existing:
            return self.save(clean_name, workspace_id=existing["id"], aliases=aliases or existing["aliases"],
                             actions=actions or existing["actions"], project_id=project_id,
                             focus_minutes=focus_minutes, enabled=enabled)
        workspace_id = self.db.execute("""INSERT INTO workspaces(name,aliases_json,actions_json,project_id,focus_minutes,enabled)
                                          VALUES(?,?,?,?,?,?)""",
                                       (clean_name, json.dumps(aliases, ensure_ascii=False), json.dumps(actions, ensure_ascii=False),
                                        project_id, focus_minutes, int(enabled)))
        return self.get(workspace_id)

    def set_active(self, workspace_id: int | None) -> None:
        with self.db.transaction() as connection:
            connection.execute("UPDATE workspaces SET active=0 WHERE active=1")
            if workspace_id is not None:
                connection.execute("UPDATE workspaces SET active=1,updated_at=CURRENT_TIMESTAMP WHERE id=?", (workspace_id,))
