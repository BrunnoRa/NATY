from __future__ import annotations

from datetime import datetime, timedelta
from database.repositories.temporal_memory import TemporalMemoryRepository
from nlu import intents
from nlu.parser import RuleParser
from tools.temporal_memory import TemporalMemoryTool
from tests.base import TempDatabaseTest


class TemporalMemoryTests(TempDatabaseTest):
    def setUp(self):
        super().setUp()
        self.repo = TemporalMemoryRepository(self.db)

    def test_events_are_ordered_and_filtered_by_date(self):
        now = datetime.now().astimezone()
        self.repo.add("TASK", "Ontem", timestamp=(now - timedelta(days=1)).isoformat(timespec="seconds"))
        self.repo.add("RESEARCH", "Hoje cedo", timestamp=(now - timedelta(minutes=2)).isoformat(timespec="seconds"))
        self.repo.add("DECISION", "Agora", timestamp=now.isoformat(timespec="seconds"))
        self.assertEqual(["Agora", "Hoje cedo"], [item["summary"] for item in self.repo.recent(2)])
        self.assertEqual(["Hoje cedo", "Agora"], [item["summary"] for item in self.repo.for_day(now.date())])

    def test_retention_removes_only_old_events(self):
        now = datetime.now().astimezone()
        self.repo.add("TASK", "Antigo", timestamp=(now - timedelta(days=100)).isoformat(timespec="seconds"))
        self.repo.add("TASK", "Recente", timestamp=now.isoformat(timespec="seconds"))
        self.assertEqual(1, self.repo.prune(90, now))
        self.assertEqual("Recente", self.repo.recent(1)[0]["summary"])

    def test_where_stopped_and_specific_intents(self):
        self.repo.add("PROJECT", "Trabalhou no projeto NATY")
        result = TemporalMemoryTool(self.repo).recall("where_stopped")
        self.assertIn("Trabalhou no projeto NATY", result.message)
        parser = RuleParser()
        self.assertEqual(intents.TEMPORAL_RECALL, parser.parse("Naty, onde paramos?").name)
        self.assertEqual("yesterday", parser.parse("O que eu fiz ontem?").entities["kind"])

    def test_significant_session_gets_deterministic_summary(self):
        self.repo.add("TASK", "Criou uma tarefa", session_id="abc")
        self.repo.add("RESEARCH", "Pesquisou Python", session_id="abc")
        summary = self.repo.summarize_session("abc")
        self.assertEqual("SESSION_SUMMARY", summary["event_type"])
        self.assertIn("Criou uma tarefa", summary["summary"])


if __name__ == "__main__": unittest.main()
