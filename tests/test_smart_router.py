from __future__ import annotations

from datetime import datetime

from core.assistant import NatyAssistant
from core.intent_router import IntentRouter
from core.models import RequestType, ResearchItem, ToolResult
from nlu import intents
from tests.base import TempDatabaseTest
from tools.windows_actions import WindowsActionsTool


class FakeSearch:
    def available(self): return True
    def search(self, query, max_results=5):
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        return [
            ResearchItem("Python", "https://docs.python.org/3/", "Python foi criado por Guido van Rossum.", observed_at=now),
            ResearchItem("Python releases", "https://www.python.org/downloads/", "Versões estáveis do Python.", observed_at=now),
        ]


class FakeReader:
    def read(self, url): return "Python foi criado por Guido van Rossum e é uma linguagem de programação."


class FakeDelegation:
    def prepare(self, question):
        return ToolResult(True, "Esse pedido se beneficia de uma análise mais profunda. Preparei o contexto e abri o ChatGPT.",
                          {"question": question}, type="delegation_ready")


class SmartRouterTests(TempDatabaseTest):
    def setUp(self):
        super().setUp()
        self.assistant = NatyAssistant(self.settings(first_run_completed=True), self.db)
        self.assistant.tool_router.research.provider = FakeSearch()
        self.assistant.tool_router.research.reader = FakeReader()
        windows = WindowsActionsTool(lambda _target: None, lambda _key: None)
        windows.delegation = FakeDelegation()
        self.assistant.tool_router.windows = windows

    def test_intelligence_acceptance_phrases_are_classified(self):
        router = IntentRouter()
        cases = {
            "Quem criou Python?": (intents.QUESTION, RequestType.QUESTION.value),
            "Qual é a versão mais recente do Python?": (intents.RESEARCH, RequestType.SEARCH.value),
            "O que eu tenho hoje?": (intents.SHOW_DAY, RequestType.PLANNING.value),
            "O que você sabe sobre meu projeto NATY?": (intents.OBSIDIAN_QUERY, RequestType.OBSIDIAN_QUERY.value),
            "Abra Spotify.": (intents.OPEN_APP, RequestType.OPEN_APP.value),
            "Próxima música.": (intents.MEDIA_CONTROL, RequestType.MEDIA.value),
            "Meu computador está lento.": (intents.SYSTEM_DIAGNOSIS, RequestType.SYSTEM.value),
            "Onde paramos ontem?": (intents.TEMPORAL_RECALL, RequestType.CONTEXT.value),
            "Me ajuda a decidir se estudo Java ou segurança.": (intents.DELEGATE, RequestType.DELEGATE.value),
            "Oi Naty.": (intents.CHAT, RequestType.CHAT.value),
            "Adiciona café na lista.": (intents.ADD_LIST_ITEMS, RequestType.LOCAL_ACTION.value),
            "Me lembra amanhã às três.": (intents.CREATE_REMINDER, RequestType.REMINDER.value),
        }
        for phrase, (intent_name, request_type) in cases.items():
            with self.subTest(phrase=phrase):
                routed = router.route(phrase)
                self.assertEqual(intent_name, routed.name)
                self.assertEqual(request_type, routed.request_type)

    def test_acceptance_phrases_do_not_fall_into_generic_clarification(self):
        phrases = (
            "Quem criou Python?", "Qual é a versão mais recente do Python?", "O que eu tenho hoje?",
            "O que você sabe sobre meu projeto NATY?", "Abra Spotify.", "Próxima música.",
            "Meu computador está lento.", "Onde paramos ontem?",
            "Me ajuda a decidir se estudo Java ou segurança.", "Oi Naty.", "Adiciona café na lista.",
        )
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                result = self.assistant.handle_result(phrase)
                self.assertNotEqual("clarification", result.type)
                self.assertNotEqual("low_confidence", result.error)

    def test_natural_questions_research_automatically_with_sources(self):
        result = self.assistant.handle_result("Quem criou Python?")
        self.assertTrue(result.ok)
        self.assertEqual("research", result.type)
        self.assertIn("Segundo as fontes", result.message)
        self.assertEqual("research", result.ui_hint["panel"])
        self.assertEqual(2, len(result.sources))

    def test_small_conversation_does_not_create_actions(self):
        self.assertEqual("Bom dia. O que você precisa?", self.assistant.handle("Bom dia."))
        response = self.assistant.handle_result("Quero estudar Java.")
        self.assertEqual("chat", response.type)
        self.assertIn("planejamento", response.message)
        self.assertEqual([], self.assistant.task_repo.list())

