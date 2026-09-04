from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from database.repositories.base import Repository


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "lista"


class ListRepository(Repository):
    def create(self, name: str) -> dict:
        existing = self.find(name)
        if existing:
            return existing
        base, slug, suffix = slugify(name), slugify(name), 2
        while self.db.one("SELECT id FROM lists WHERE slug = ?", (slug,)):
            slug, suffix = f"{base}-{suffix}", suffix + 1
        list_id = self.db.execute("INSERT INTO lists(name, slug) VALUES (?, ?)", (name.strip(), slug))
        self.activity("created", "list", list_id, name)
        return self.get(list_id)

    def get(self, list_id: int) -> dict | None:
        row = self.db.one("SELECT * FROM lists WHERE id = ?", (list_id,))
        return dict(row) if row else None

    def find(self, name: str) -> dict | None:
        cleaned = name.strip()
        row = self.db.one("SELECT * FROM lists WHERE name = ? COLLATE NOCASE OR slug = ?", (cleaned, slugify(cleaned)))
        return dict(row) if row else None

    def all(self) -> list[dict]:
        return [dict(r) for r in self.db.query("SELECT * FROM lists ORDER BY name")]

    def add_item(self, list_id: int, text: str, quantity: float | None = None) -> dict:
        existing = self.db.one("SELECT * FROM list_items WHERE list_id = ? AND text = ? COLLATE NOCASE AND checked = 0", (list_id, text.strip()))
        if existing:
            return dict(existing)
        item_id = self.db.execute("INSERT INTO list_items(list_id, text, quantity) VALUES (?, ?, ?)", (list_id, text.strip(), quantity))
        self.db.execute("UPDATE lists SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (list_id,))
        self.activity("created", "list_item", item_id, text)
        return self.item(item_id)

    def item(self, item_id: int) -> dict | None:
        row = self.db.one("SELECT * FROM list_items WHERE id = ?", (item_id,))
        return dict(row) if row else None

    def items(self, list_id: int, checked: bool | None = None) -> list[dict]:
        if checked is None:
            rows = self.db.query("SELECT * FROM list_items WHERE list_id = ? ORDER BY checked, id", (list_id,))
        else:
            rows = self.db.query("SELECT * FROM list_items WHERE list_id = ? AND checked = ? ORDER BY id", (list_id, int(checked)))
        return [dict(r) for r in rows]

    def find_item(self, list_id: int, text: str) -> dict | None:
        row = self.db.one("SELECT * FROM list_items WHERE list_id = ? AND text = ? COLLATE NOCASE ORDER BY checked, id LIMIT 1", (list_id, text.strip()))
        return dict(row) if row else None

    def check(self, list_id: int, text: str, checked: bool = True) -> dict | None:
        item = self.find_item(list_id, text)
        if not item:
            return None
        completed = datetime.now().astimezone().isoformat(timespec="seconds") if checked else None
        self.db.execute("UPDATE list_items SET checked = ?, completed_at = ? WHERE id = ?", (int(checked), completed, item["id"]))
        self.activity("updated", "list_item", item["id"], "checked" if checked else "unchecked")
        return self.item(item["id"])

    def remove(self, list_id: int, text: str) -> bool:
        item = self.find_item(list_id, text)
        if not item:
            return False
        self.db.execute("DELETE FROM list_items WHERE id = ?", (item["id"],))
        self.activity("deleted", "list_item", item["id"], text)
        return True

    def clear_checked(self, list_id: int) -> int:
        with self.db.transaction() as conn:
            count = conn.execute("SELECT COUNT(*) FROM list_items WHERE list_id = ? AND checked = 1", (list_id,)).fetchone()[0]
            conn.execute("DELETE FROM list_items WHERE list_id = ? AND checked = 1", (list_id,))
        return int(count)
