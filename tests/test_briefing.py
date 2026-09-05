from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

from database.repositories.reminders import ReminderRepository
from database.repositories.tasks import TaskRepository
from nlu import intents
from nlu.parser import RuleParser
from tools.briefing import BriefingTool
from tests.base import TempDatabaseTest


class FakeAuth:
    def available(self): return True
class FakeCalendar:
    def between(self, *_args, **_kwargs):
        return [{"summary": "Aula", "start": {"dateTime": "2026-09-05T14:00:00-03:00"}}]
class FakeGmail:
    def search(self, *_args, **_kwargs): return []


class BriefingTests(TempDatabaseTest):
    def setUp(self):
        super().setUp()
        self.tasks, self.reminders = TaskRepository(self.db), ReminderRepository(self.db)
        self.now = datetime.fromisoformat("2026-09-05T09:00:00-03:00")

    def tool(self, google=None): return BriefingTool(self.db, self.tasks, self.reminders, google)

    def test_briefing_without_google_and_without_tasks(self):
        result = self.tool().build(self.now)
        self.assertIn("não tem tarefas", result.message)
        self.assertFalse(result.data["google_connected"])

    def test_briefing_includes_overdue_task(self):
        self.tasks.create("Entregar relatório", due_at=(self.now - timedelta(hours=2)).isoformat())
        result = self.tool().build(self.now)
        self.assertIn("tarefa(s) vencida(s)", result.data["attention"][0]["title"])

    def test_briefing_uses_optional_fake_calendar(self):
        google = SimpleNamespace(settings=SimpleNamespace(google_enabled=True), auth=FakeAuth(),
                                 calendar=FakeCalendar(), gmail=FakeGmail())
        result = self.tool(google).build(self.now)
        self.assertEqual("Aula", result.data["now"][0]["title"])
        self.assertTrue(result.data["google_connected"])

    def test_briefing_intents(self):
        parser = RuleParser()
        self.assertEqual(intents.DAILY_BRIEFING, parser.parse("Bom dia Naty").name)
        self.assertEqual(intents.DAILY_BRIEFING, parser.parse("Naty, me dá meu briefing").name)


if __name__ == "__main__": unittest.main()
