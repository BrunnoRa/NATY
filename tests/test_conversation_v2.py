from core.assistant import NatyAssistant
from tests.base import TempDatabaseTest


class ConversationV2Tests(TempDatabaseTest):
    def setUp(self):
        super().setUp()
        self.assistant = NatyAssistant(self.settings(first_run_completed=True), self.db)

    def test_memory_requires_explicit_phrase(self):
        self.assistant.handle("eu gosto de chá")
        self.assertEqual(self.assistant.memory_repo.all(), [])
        response = self.assistant.handle("lembre que eu prefiro chá sem açúcar")
        self.assertIn("lembrar", response.lower())
        self.assertEqual(len(self.assistant.memory_repo.all()), 1)

    def test_tired_flow_suggests_shortest_task(self):
        self.assistant.task_repo.create("Longa", estimated_minutes=90)
        self.assistant.task_repo.create("Curta", estimated_minutes=10)
        response = self.assistant.handle("estou cansada hoje")
        self.assertIn("Curta", response)

    def test_unknown_has_deterministic_fallback_without_ai(self):
        response = self.assistant.handle("queria pensar em uma coisa")
        self.assertIn("Entendi", response)
