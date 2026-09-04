from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from ai.llama_cpp import LlamaCppProvider
from ai.no_ai import NoAIProvider
from config import Settings
from core.context import SessionContext
from core.event_bus import EventBus
from core.intent_router import IntentRouter
from core.agent_router import AgentRouter
from core.models import AppState, ToolResult
from core.response_formatter import ResponseFormatter
from core.tool_router import ToolRouter
from database.connection import Database
from database.migrations import migrate
from database.repositories.lists import ListRepository
from database.repositories.memories import MemoryRepository
from database.repositories.projects import ProjectRepository
from database.repositories.reminders import ReminderRepository
from database.repositories.tasks import TaskRepository
from planner.planner import Planner
from conversation.engine import ConversationEngine
from knowledge.graph import KnowledgeGraph
from knowledge.obsidian_index import ObsidianIndex
from knowledge.retriever import ObsidianContextRetriever
from skills.registry import build_registry
from tools.lists import ListsTool
from tools.calendar import CalendarTool
from tools.notes import NotesTool
from tools.obsidian import ObsidianTool
from tools.projects import ProjectsTool
from tools.reminders import RemindersTool
from tools.research import ResearchTool
from tools.tasks import TasksTool
from research.perplexity_provider import PerplexityProvider
from connectors.google.auth import GoogleAuth
from connectors.google.gmail import GmailConnector
from connectors.google.calendar import GoogleCalendarConnector
from connectors.registry import ConnectorRegistry
from tools.google_workspace import GoogleWorkspaceTool


def setup_logging(settings: Settings) -> logging.Logger:
    settings.logs_path.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("naty")
    if not logger.handlers:
        handler = RotatingFileHandler(settings.logs_path / "naty.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler); logger.setLevel(logging.INFO)
    return logger


class NatyAssistant:
    def __init__(self, settings: Settings | None = None, database: Database | None = None):
        self.settings = settings or Settings.load()
        self.logger = setup_logging(self.settings)
        self.db = database or Database(self.settings.database_path)
        migrate(self.db)
        self.context, self.events = SessionContext(), EventBus()
        task_repo, list_repo = TaskRepository(self.db), ListRepository(self.db)
        project_repo, reminder_repo = ProjectRepository(self.db), ReminderRepository(self.db)
        self.reminder_repo, self.memory_repo = reminder_repo, MemoryRepository(self.db)
        self.task_repo, self.list_repo, self.project_repo = task_repo, list_repo, project_repo
        managed_obsidian = str(self.settings.managed_obsidian_path or "")
        self.obsidian = ObsidianTool(
            self.settings.obsidian_enabled, self.settings.obsidian_vault_path, list_repo, managed_obsidian
        )
        task_tool, list_tool = TasksTool(task_repo), ListsTool(list_repo, self.obsidian)
        reminder_tool, project_tool = RemindersTool(reminder_repo), ProjectsTool(project_repo)
        notes_tool = NotesTool(self.db, self.obsidian)
        self.connectors = ConnectorRegistry()
        google_auth = GoogleAuth.for_settings(self.settings)
        self.connectors.register("gmail", lambda: GmailConnector(google_auth))
        self.connectors.register("google_calendar", lambda: GoogleCalendarConnector(google_auth))
        google_tool = GoogleWorkspaceTool(
            self.settings, self.db, google_auth,
            self.connectors.get("gmail"), self.connectors.get("google_calendar"),
        )
        perplexity = PerplexityProvider(enabled=self.settings.perplexity_enabled, timeout=self.settings.research_timeout_seconds)
        research_provider = perplexity if perplexity.available() else None
        research_tool = ResearchTool(self.db, provider=research_provider, max_results=self.settings.max_search_results,
            timeout=self.settings.research_timeout_seconds, max_size=self.settings.max_response_size,
            obsidian=self.obsidian, enabled=self.settings.research_enabled)
        self.intent_router, self.formatter = IntentRouter(), ResponseFormatter()
        self.tool_router = ToolRouter(tasks=task_tool, lists=list_tool, reminders=reminder_tool,
            projects=project_tool, notes=notes_tool, calendar=CalendarTool(self.db), planner=Planner(task_repo), research=research_tool, context=self.context, google=google_tool)
        self.ai = LlamaCppProvider(self.settings.ai_model_path, self.settings.ai_threads, self.settings.ai_context_size,
            self.settings.ai_idle_unload_seconds, self.settings.ai_max_ram_mb, self.settings.ai_min_available_ram_mb) if self.settings.ai_enabled else NoAIProvider()
        self.obsidian_index = ObsidianIndex(
            self.db, self.settings.obsidian_vault_path, self.obsidian.base
        ) if self.obsidian.available else None
        if self.obsidian_index:
            try: self.obsidian_index.index()
            except Exception: self.logger.exception("Falha ao indexar Obsidian")
        self.knowledge_graph = KnowledgeGraph(self.db)
        try: self.knowledge_graph.rebuild()
        except Exception: self.logger.exception("Falha ao gerar grafo")
        retriever = ObsidianContextRetriever(self.obsidian_index, project_repo, task_repo,
            self.settings.obsidian_max_notes, self.settings.obsidian_max_chars)
        self.conversation = ConversationEngine(context=self.context, tasks=task_repo, lists=list_repo,
            memories=self.memory_repo, planner=Planner(task_repo), retriever=retriever, ai=self.ai)
        self.skills = build_registry(self.tool_router)
        self.agent_router = AgentRouter(self.intent_router, self.skills, self.conversation, self.events)
        self.state = AppState.IDLE

    def handle(self, text: str) -> str:
        self.state = AppState.PROCESSING; self.events.publish("state", self.state)
        try:
            result, route_name = self.agent_router.handle(text)
            if result.entity_type and result.entity_id:
                label = result.data.get("title", result.data.get("name", "")) if isinstance(result.data, dict) else ""
                self.context.set_entity(result.entity_type, result.entity_id, label)
            response = self.formatter.format(result)
            self.context.remember_turn(text, response)
            self.db.execute("INSERT INTO activity_history(action, summary) VALUES ('command', ?)", (route_name,))
            return response
        except Exception:
            self.logger.exception("Falha ao processar comando")
            self.state = AppState.ERROR; self.events.publish("state", self.state)
            return "Algo deu errado ao executar esse pedido. Seus dados continuam seguros; consulte o log para detalhes."
        finally:
            self.state = AppState.IDLE; self.events.publish("state", self.state)

    def close(self) -> None:
        try:
            self.ai.unload()
        except AttributeError:
            pass
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)
