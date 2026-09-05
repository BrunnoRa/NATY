from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
import gc
import tempfile
import time
import unittest

from database.connection import Database
from database.migrations import migrate
from database.repositories.notifications import NotificationRepository
from database.repositories.reminders import ReminderRepository
from database.repositories.tasks import TaskRepository
from nlu import intents
from nlu.parser import RuleParser
from proactivity.manager import ProactivityManager
from tools.notifications import NotificationTool


class ProactivityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temporary.name) / "naty.db")
        migrate(self.db)
        self.tasks, self.reminders = TaskRepository(self.db), ReminderRepository(self.db)
        self.notifications = NotificationRepository(self.db)
        self.emitted = []
        self.settings = SimpleNamespace(proactivity_level="important", quiet_hours_enabled=False,
                                        quiet_hours_start="22:00", quiet_hours_end="07:00")
        self.manager = ProactivityManager(self.settings, self.db, self.tasks, self.reminders,
                                           self.notifications, lambda *args: self.emitted.append(args))
        self.now = datetime.fromisoformat("2026-09-05T12:00:00-03:00")

    def tearDown(self):
        for attempt in range(3):
            try:
                self.temporary.cleanup()
                break
            except OSError:
                if attempt == 2: raise
                gc.collect(); time.sleep(0.05)

    def test_cooldown_prevents_repeated_event(self):
        self.assertTrue(self.manager.consider("same", "TASK", "IMPORTANT", "A", "B", now=self.now, cooldown_minutes=60))
        self.assertFalse(self.manager.consider("same", "TASK", "IMPORTANT", "A", "B", now=self.now + timedelta(minutes=30), cooldown_minutes=60))
        self.assertEqual(1, len(self.notifications.list()))

    def test_quiet_hours_allows_only_urgent(self):
        self.settings.quiet_hours_enabled = True
        quiet = self.now.replace(hour=23)
        self.assertFalse(self.manager.consider("normal", "TASK", "IMPORTANT", "A", "B", now=quiet))
        self.assertTrue(self.manager.consider("urgent", "SYSTEM", "URGENT", "A", "B", now=quiet))

    def test_off_and_important_levels_filter_suggestions(self):
        self.assertFalse(self.manager.consider("info", "NATY", "INFO", "A", "B", now=self.now))
        self.settings.proactivity_level = "off"
        self.assertFalse(self.manager.consider("urgent", "SYSTEM", "URGENT", "A", "B", now=self.now))

    def test_overdue_scan_and_notification_commands(self):
        self.tasks.create("Atrasada", due_at=(self.now - timedelta(hours=1)).isoformat())
        self.assertEqual(1, self.manager.scan(self.now))
        result = NotificationTool(self.notifications).show(important_only=True)
        self.assertIn("1 notificação", result.message)
        parser = RuleParser()
        self.assertEqual(intents.NOTIFICATION_LIST, parser.parse("Naty, tem algo importante?").name)


if __name__ == "__main__": unittest.main()
