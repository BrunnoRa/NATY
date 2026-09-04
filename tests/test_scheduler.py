from datetime import datetime, timedelta

from database.repositories.reminders import ReminderRepository
from database.repositories.tasks import TaskRepository
from scheduler.scheduler import Scheduler
from tests.base import TempDatabaseTest


class SchedulerTests(TempDatabaseTest):
    def test_due_reminder_notifies_once(self):
        reminders, tasks, calls = ReminderRepository(self.db), TaskRepository(self.db), []
        reminders.create("Ligar", (datetime.now().astimezone()-timedelta(minutes=1)).isoformat())
        scheduler = Scheduler(reminders, tasks, lambda title, message: calls.append((title, message)))
        scheduler.check_once(); scheduler.check_once()
        self.assertEqual(len(calls), 1)

    def test_overdue_task_antispam(self):
        reminders, tasks, calls = ReminderRepository(self.db), TaskRepository(self.db), []
        tasks.create("Atrasada", due_at=(datetime.now().astimezone()-timedelta(days=1)).isoformat())
        scheduler = Scheduler(reminders, tasks, lambda title, message: calls.append((title, message)))
        scheduler.check_once(); scheduler.check_once()
        self.assertEqual(len(calls), 1)
