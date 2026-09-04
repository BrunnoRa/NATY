from database.migrations import MIGRATIONS, migrate
from database.repositories.memories import MemoryRepository
from tests.base import TempDatabaseTest


class DatabaseTests(TempDatabaseTest):
    def test_all_required_tables_exist(self):
        names = {r["name"] for r in self.db.query("SELECT name FROM sqlite_master WHERE type='table'")}
        expected = {"tasks", "projects", "reminders", "appointments", "lists", "list_items", "notes", "memories", "preferences", "activity_history", "research_history"}
        self.assertTrue(expected <= names)

    def test_migration_is_idempotent(self):
        migrate(self.db); migrate(self.db)
        self.assertEqual(self.db.one("SELECT COUNT(*) c FROM schema_migrations")["c"], len(MIGRATIONS))

    def test_foreign_keys_are_enabled(self):
        conn = self.db.connect()
        try: self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        finally: conn.close()

    def test_memory_crud(self):
        repo = MemoryRepository(self.db)
        memory = repo.set("preference", "study_block", "30")
        self.assertEqual(memory["value"], "30")
        updated = repo.set("preference", "study_block", "45")
        self.assertEqual(updated["value"], "45")
        self.assertTrue(repo.delete(updated["id"])); self.assertEqual(repo.all(), [])
