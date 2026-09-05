from __future__ import annotations

from datetime import datetime, timedelta

from core.assistant import NatyAssistant
from core.intent_router import IntentRouter
from core.models import RequestType, ResearchItem
from ipc.handler import CoreRequestHandler
from ipc.protocol import request
from knowledge.context import ContextNote, ContextPack
from tools.knowledge_query import KnowledgeQueryTool
from tools.windows_actions import WindowsActionsTool
from scheduler.scheduler import Scheduler
from tests.base import TempDatabaseTest


class FakeSearch:
    def available(self):
        return True

    def search(self, query, max_results=5):
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        return [
            ResearchItem("Fonte real A", "https://example.com/a", "Fato verificável A.", source="example.com", observed_at=now),
            ResearchItem("Fonte real B", "https://example.org/b", "Fato verificável B.", source="example.org", observed_at=now),
        ]


class FakeRetriever:
    def retrieve(self, query):
        return ContextPack(query, [ContextNote("TCC", "03 - Projetos/TCC.md", "O TCC estuda agentes pessoais locais.", 1.0)])


class FunctionalCycleTests(TempDatabaseTest):
    def setUp(self):
        super().setUp()
        self.assistant = NatyAssistant(self.settings(first_run_completed=True), self.db)

    def test_required_request_types_are_classified(self):
        router = IntentRouter()
        cases = {
            "Oi Naty": RequestType.CHAT.value,
            "Que horas são?": RequestType.QUESTION.value,
            "O que eu tenho hoje?": RequestType.PLANNING.value,
            "Adiciona café na lista": RequestType.LOCAL_ACTION.value,
            "Me lembra amanhã às 15h de ligar": RequestType.REMINDER.value,
            "Pesquisa preço da RX 7600": RequestType.SEARCH.value,
            "Compare RX 7600 e RTX 4060": RequestType.DEEP_RESEARCH.value,
            "O que você sabe sobre meu TCC?": RequestType.OBSIDIAN_QUERY.value,
            "Abra o Spotify": RequestType.OPEN_APP.value,
            "Próxima música": RequestType.MEDIA.value,
            "Todo domingo às 19h me lembra de planejar": RequestType.AUTOMATION.value,
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(router.route(text).request_type, expected)

    def test_greeting_and_unknown_never_use_generic_success(self):
        self.assertEqual(self.assistant.handle("Oi Naty"), "Oi! O que você precisa?")
        unknown = self.assistant.handle("uma frase sem intenção reconhecível")
        self.assertIn("Não consegui identificar", unknown)
        self.assertNotIn("Entendi.", unknown)

    def test_list_task_day_and_named_completion_execute_real_data(self):
        added = self.assistant.handle_result("Adiciona café na minha lista")
        self.assertTrue(added.ok)
        shopping = self.assistant.list_repo.find("Lista de Compras")
        self.assertEqual(self.assistant.list_repo.items(shopping["id"])[0]["text"], "café")

        created = self.assistant.handle_result("Adiciona estudar Java amanhã")
        self.assertTrue(created.ok)
        day = self.assistant.handle_result("O que eu tenho amanhã?")
        self.assertEqual(day.ui_hint["panel"], "today")
        self.assertEqual(day.data["tasks"][0]["title"], "estudar Java")
        completed = self.assistant.handle_result("Marca estudar Java como concluída")
        self.assertEqual(completed.type, "task_completed")

    def test_reminder_and_weekly_automation_are_persisted(self):
        reminder = self.assistant.handle_result("Me lembra amanhã às três de falar com o professor")
        self.assertTrue(reminder.ok)
        self.assertIn("15:00", reminder.data["remind_at"])
        automation = self.assistant.handle_result("Todo domingo às 19h me lembra de planejar minha semana")
        self.assertTrue(automation.ok)
        self.assertEqual(automation.type, "automation_created")
        self.assertEqual(self.assistant.automation_repo.list()[0]["trigger_value"], "WEEKLY")

    def test_due_automation_runs_once_and_is_disabled(self):
        due = (datetime.now().astimezone() - timedelta(minutes=1)).isoformat(timespec="minutes")
        automation = self.assistant.automation_repo.create("Beber água", "ONE_TIME", due, {"text": "Beber água"})
        calls = []
        Scheduler(self.assistant.reminder_repo, self.assistant.task_repo, lambda title, message: calls.append((title, message)),
                  settings=self.assistant.settings, automations=self.assistant.automation_repo).check_once()
        self.assertEqual(calls, [("Automação da Naty", "Beber água")])
        self.assertFalse(self.assistant.automation_repo.get(automation["id"])["enabled"])

    def test_search_knowledge_launcher_media_and_ipc_return_real_results(self):
        self.assistant.tool_router.research.provider = FakeSearch()
        research = self.assistant.handle_result("Pesquisa novidades de inteligência artificial")
        self.assertTrue(research.ok)
        self.assertEqual(research.ui_hint["panel"], "research")
        self.assertEqual(len(research.sources), 2)
        self.assertIn("retrieved_at", research.sources[0])

        knowledge = KnowledgeQueryTool(FakeRetriever()).query("TCC")
        self.assertIn("agentes pessoais locais", knowledge.message)

        opened, keys = [], []
        self.assistant.tool_router.windows = WindowsActionsTool(opened.append, keys.append)
        self.assertTrue(self.assistant.handle_result("Abra o Spotify").ok)
        self.assertEqual(opened, ["spotify:"])
        self.assertTrue(self.assistant.handle_result("Próxima música").ok)
        self.assertEqual(keys, [0xB0])

        response = CoreRequestHandler(self.assistant).handle(request("user_input", {"text": "Mostra meu dia"}, "cycle"))
        payload = response["payload"]
        self.assertIn("success", payload)
        self.assertEqual(payload["ui"]["panel"], "today")
        self.assertIn("data", payload)
