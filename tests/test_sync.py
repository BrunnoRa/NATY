from __future__ import annotations

import json
import gc
from pathlib import Path
import tempfile
import time
import unittest

from database.connection import Database
from database.migrations import migrate
from sync.manager import SyncManager
from sync.models import DeviceIdentity


class SyncManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.shared = self.root / "NatySync"
        self.db_a = Database(self.root / "device-a" / "naty.db")
        self.db_b = Database(self.root / "device-b" / "naty.db")
        migrate(self.db_a)
        migrate(self.db_b)
        self.identity_a = DeviceIdentity.load_or_create(self.root / "device-a" / "identity.json", "desktop-brunno")
        self.identity_b = DeviceIdentity.load_or_create(self.root / "device-b" / "identity.json", "notebook-brunno")
        self.sync_a = SyncManager(self.db_a, self.shared, self.identity_a)
        self.sync_b = SyncManager(self.db_b, self.shared, self.identity_b)

    def tearDown(self):
        self.sync_a.stop()
        self.sync_b.stop()
        for attempt in range(3):
            try:
                self.temp.cleanup()
                break
            except OSError:
                if attempt == 2:
                    raise
                gc.collect()
                time.sleep(0.05)

    def test_device_identity_is_persistent_uuid_and_not_hostname(self):
        restored = DeviceIdentity.load_or_create(self.root / "device-a" / "identity.json", "outro-nome")
        self.assertEqual(self.identity_a.device_id, restored.device_id)
        self.assertTrue(self.identity_a.device_id.startswith("desktop-brunno-"))
        self.assertNotEqual(self.identity_a.device_id, "desktop-brunno")

    def test_round_trip_is_idempotent_and_keeps_local_sqlite(self):
        task_id_a = self.db_a.execute(
            "INSERT INTO tasks(title,description,status,priority) VALUES(?,?,?,?)",
            ("Preparar apresentação", "Slides finais", "pending", "high"),
        )
        created = self.sync_a.record("task", task_id_a, "create", dict(self.db_a.one("SELECT * FROM tasks WHERE id=?", (task_id_a,))))

        imported = self.sync_b.sync_now()
        self.assertEqual(1, imported["applied"])
        task_id_b = self.sync_b.state.local_id("task", created.entity_id)
        self.assertIsNotNone(task_id_b)
        self.assertEqual("Preparar apresentação", self.db_b.one("SELECT title FROM tasks WHERE id=?", (task_id_b,))["title"])

        self.db_b.execute("UPDATE tasks SET status='completed' WHERE id=?", (task_id_b,))
        self.sync_b.record("task", task_id_b, "complete", dict(self.db_b.one("SELECT * FROM tasks WHERE id=?", (task_id_b,))))
        completed = self.sync_a.sync_now()
        self.assertEqual(1, completed["applied"])
        self.assertEqual("completed", self.db_a.one("SELECT status FROM tasks WHERE id=?", (task_id_a,))["status"])

        reminder_id_a = self.db_a.execute(
            "INSERT INTO reminders(text,remind_at,status) VALUES(?,?,?)",
            ("Falar com o professor", "2026-09-06T15:00:00-03:00", "pending"),
        )
        self.sync_a.record("reminder", reminder_id_a, "create",
                           dict(self.db_a.one("SELECT * FROM reminders WHERE id=?", (reminder_id_a,))))
        reminder_sync = self.sync_b.sync_now()
        self.assertEqual(1, reminder_sync["applied"])
        self.assertEqual(1, self.db_b.one("SELECT COUNT(*) AS total FROM reminders")["total"])

        reapplied = self.sync_b.sync_now()
        self.assertEqual(0, reapplied["applied"])
        self.assertEqual(1, self.db_b.one("SELECT COUNT(*) AS total FROM tasks")["total"])
        self.assertEqual(1, self.db_b.one("SELECT COUNT(*) AS total FROM reminders")["total"])
        self.assertFalse(list(self.shared.rglob("*.tmp")))

    def test_concurrent_edits_create_conflict_without_losing_content(self):
        task_id_a = self.db_a.execute("INSERT INTO tasks(title) VALUES(?)", ("Título original",))
        created = self.sync_a.record("task", task_id_a, "create",
                                     dict(self.db_a.one("SELECT * FROM tasks WHERE id=?", (task_id_a,))))
        self.sync_b.sync_now()
        task_id_b = self.sync_b.state.local_id("task", created.entity_id)

        self.db_a.execute("UPDATE tasks SET title=? WHERE id=?", ("Edição do desktop", task_id_a))
        self.sync_a.record("task", task_id_a, "update",
                           dict(self.db_a.one("SELECT * FROM tasks WHERE id=?", (task_id_a,))))
        self.db_b.execute("UPDATE tasks SET title=? WHERE id=?", ("Edição do notebook", task_id_b))
        self.sync_b.record("task", task_id_b, "update",
                           dict(self.db_b.one("SELECT * FROM tasks WHERE id=?", (task_id_b,))))

        result_a = self.sync_a.sync_now()
        result_b = self.sync_b.sync_now()
        self.assertGreaterEqual(result_a["conflicts"] + result_b["conflicts"], 1)
        self.assertEqual("Edição do desktop", self.db_a.one("SELECT title FROM tasks WHERE id=?", (task_id_a,))["title"])
        self.assertEqual("Edição do notebook", self.db_b.one("SELECT title FROM tasks WHERE id=?", (task_id_b,))["title"])
        self.assertTrue(self.sync_a.state.conflicts() or self.sync_b.state.conflicts())
        conflict_files = list((self.shared / "conflicts").glob("*.json"))
        self.assertTrue(conflict_files)
        saved = json.loads(conflict_files[0].read_text(encoding="utf-8"))
        self.assertNotEqual(saved["local_payload"]["title"], saved["incoming_payload"]["title"])

    def test_delete_uses_tombstone_and_does_not_erase_history(self):
        project_id = self.db_a.execute("INSERT INTO projects(name) VALUES(?)", ("Projeto temporário",))
        created = self.sync_a.record("project", project_id, "create",
                                     dict(self.db_a.one("SELECT * FROM projects WHERE id=?", (project_id,))))
        self.sync_b.sync_now()
        project_id_b = self.sync_b.state.local_id("project", created.entity_id)
        self.db_a.execute("DELETE FROM projects WHERE id=?", (project_id,))
        deletion = self.sync_a.record("project", project_id, "delete", {"name": "Projeto temporário"})
        self.sync_b.sync_now()

        self.assertIsNone(self.db_b.one("SELECT * FROM projects WHERE id=?", (project_id_b,)))
        state = self.sync_b.state.state("project", created.entity_id)
        self.assertEqual(1, state["tombstone"])
        event_files = list((self.shared / "events").glob("*.json"))
        self.assertEqual(2, len(event_files))
        self.assertTrue(any(json.loads(path.read_text(encoding="utf-8"))["event_id"] == deletion.event_id
                            for path in event_files))


if __name__ == "__main__":
    unittest.main()
