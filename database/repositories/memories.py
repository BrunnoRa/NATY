from database.repositories.base import Repository


class MemoryRepository(Repository):
    def set(self, type_: str, key: str, value: str, confidence: float = 1.0, expires_at: str | None = None) -> dict:
        self.db.execute(
            """INSERT INTO memories(type, key, value, confidence, expires_at) VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(type, key) DO UPDATE SET value=excluded.value, confidence=excluded.confidence,
               expires_at=excluded.expires_at, updated_at=CURRENT_TIMESTAMP""",
            (type_, key, value, confidence, expires_at),
        )
        row = self.db.one("SELECT * FROM memories WHERE type = ? AND key = ?", (type_, key))
        return dict(row)

    def all(self) -> list[dict]:
        return [dict(r) for r in self.db.query("SELECT * FROM memories ORDER BY type, key")]

    def delete(self, memory_id: int) -> bool:
        exists = self.db.one("SELECT id FROM memories WHERE id = ?", (memory_id,))
        if not exists: return False
        self.db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        return True
