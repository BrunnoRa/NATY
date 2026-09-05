from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import re

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
from database.repositories.automations import AutomationRepository
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
from tools.automations import AutomationsTool
from tools.knowledge_query import KnowledgeQueryTool
from tools.planning import PlanningTool
from tools.windows_actions import WindowsActionsTool
from scheduler.scheduler import Scheduler
from research.perplexity_provider import PerplexityProvider
from connectors.google.auth import GoogleAuth
from connectors.google.gmail import GmailConnector
from connectors.google.calendar import GoogleCalendarConnector
from connectors.registry import ConnectorRegistry
from tools.google_workspace import GoogleWorkspaceTool
from delegation.external_ai import ChatGPTWebProvider, ExternalResultImporter
from learning.manager import LearningManager
from sync.manager import SyncManager
from sync.models import DeviceIdentity
from diagnostics.service import DiagnosticService


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
        automation_repo = AutomationRepository(self.db)
        self.reminder_repo, self.memory_repo = reminder_repo, MemoryRepository(self.db)
        self.task_repo, self.list_repo, self.project_repo, self.automation_repo = task_repo, list_repo, project_repo, automation_repo
        self.notifications: list[dict[str, str]] = []
        self.scheduler: Scheduler | None = None
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
        self.google = google_tool
        perplexity = PerplexityProvider(enabled=self.settings.perplexity_enabled, timeout=self.settings.research_timeout_seconds)
        research_provider = perplexity if perplexity.available() else None
        research_tool = ResearchTool(self.db, provider=research_provider, max_results=self.settings.max_search_results,
            timeout=self.settings.research_timeout_seconds, max_size=self.settings.max_response_size,
            obsidian=self.obsidian, enabled=self.settings.research_enabled)
        self.intent_router, self.formatter = IntentRouter(), ResponseFormatter()
        self.tool_router = ToolRouter(tasks=task_tool, lists=list_tool, reminders=reminder_tool,
            projects=project_tool, notes=notes_tool, calendar=CalendarTool(self.db), planner=Planner(task_repo), research=research_tool,
            context=self.context, google=google_tool, automations=AutomationsTool(automation_repo), windows=WindowsActionsTool(),
            planning=PlanningTool(self.db, task_tool, reminder_repo))
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
        self.external_importer = ExternalResultImporter()
        self.learning = LearningManager(self.memory_repo, self.obsidian, self.settings.learning_mode)
        if self.tool_router.windows and self.settings.chatgpt_handoff_enabled:
            self.tool_router.windows.delegation = ChatGPTWebProvider(
                retriever, self.tool_router.windows._copy_text, self.tool_router.windows.opener)
        self.tool_router.knowledge = KnowledgeQueryTool(retriever)
        self.conversation = ConversationEngine(context=self.context, tasks=task_repo, lists=list_repo,
            memories=self.memory_repo, planner=Planner(task_repo), retriever=retriever, ai=self.ai)
        self.skills = build_registry(self.tool_router)
        self.agent_router = AgentRouter(self.intent_router, self.skills, self.conversation, self.events)
        self.sync: SyncManager | None = None
        if self.settings.sync_enabled and self.settings.sync_folder:
            try:
                identity = DeviceIdentity.load_or_create(
                    self.settings.resolve_path(self.settings.data_dir) / "device_identity.json",
                    self.settings.device_name,
                )
                self.sync = SyncManager(
                    self.db, self.settings.resolve_path(self.settings.sync_folder), identity,
                    on_applied=self._refresh_synced_indexes,
                )
                self.sync.start()
            except (OSError, ValueError):
                self.logger.exception("Falha ao iniciar sincronização")
        self.state = AppState.IDLE
        self.diagnostics = DiagnosticService(self)

    def handle_result(self, text: str) -> ToolResult:
        self.state = AppState.PROCESSING; self.events.publish("state", self.state)
        try:
            plain = text.strip().casefold()
            if re.fullmatch(r"(?:naty[,.]?\s*)?como (?:você|voce) está[?.!]*", plain):
                report = self.diagnostics.run()
                return ToolResult(True, report["summary"], report, type="diagnostics")
            if self.learning.pending and plain in {"sim", "confirmo", "pode", "pode fazer"}:
                return self.learning.confirm()
            if self.learning.pending and plain in {"não", "nao", "cancelar", "cancela"}:
                return self.learning.cancel()
            import_match = re.search(r"(?is)^(?:importar resultado externo|resultado do chatgpt)\s*[:\n]\s*(.+)$", text.strip())
            if import_match:
                result = self.external_importer.result(import_match.group(1))
                if result.ok: self.learning.queue_external(result.data)
                return result
            candidate = self.learning.detect(text)
            if candidate:
                return self.learning.propose(candidate)
            result, route_name = self.agent_router.handle(text)
            try:
                self._record_sync_result(result)
            except Exception:
                if self.sync:
                    self.sync.status = "offline"
                self.logger.exception("Falha ao registrar evento de sincronização")
            if result.entity_type and result.entity_id:
                label = result.data.get("title", result.data.get("name", "")) if isinstance(result.data, dict) else ""
                self.context.set_entity(result.entity_type, result.entity_id, label)
            response = self.formatter.format(result)
            result.message = response
            self.context.remember_turn(text, response)
            self.db.execute("INSERT INTO activity_history(action, summary) VALUES ('command', ?)", (route_name,))
            return result
        except Exception:
            self.logger.exception("Falha ao processar comando")
            self.state = AppState.ERROR; self.events.publish("state", self.state)
            return ToolResult(False, "Algo deu errado ao executar esse pedido. Seus dados continuam seguros; consulte o log para detalhes.",
                              type="internal_error", error="internal_error")
        finally:
            self.state = AppState.IDLE; self.events.publish("state", self.state)

    def handle(self, text: str) -> str:
        return self.handle_result(text).message

    def start_scheduler(self) -> None:
        if self.scheduler:
            return
        self.scheduler = Scheduler(self.reminder_repo, self.task_repo, self._notify,
                                   self.settings.scheduler_interval_seconds, self.settings, self.automation_repo)
        self.scheduler.start()

    def _notify(self, title: str, message: str) -> None:
        self.notifications.append({"title": title, "message": message})

    def drain_notifications(self) -> list[dict[str, str]]:
        current, self.notifications = self.notifications[:], []
        return current

    def _record_sync_result(self, result: ToolResult) -> None:
        if not self.sync or not result.ok:
            return
        action_by_type = {
            "create_task": ("task", "create"),
            "task_completed": ("task", "complete"),
            "complete_last": ("task", "complete"),
            "update_last": ("task", "update"),
            "postpone_last": ("task", "update"),
            "create_reminder": ("reminder", "create"),
            "create_project": ("project", "create"),
            "automation_created": ("automation", "create"),
        }
        mapped = action_by_type.get(result.type)
        if mapped and result.entity_id and isinstance(result.data, dict):
            self.sync.record(mapped[0], result.entity_id, mapped[1], dict(result.data))
        elif result.type == "add_list_items" and isinstance(result.data, list):
            for item in result.data:
                if isinstance(item, dict) and item.get("id"):
                    payload = dict(item)
                    list_row = self.db.one("SELECT name FROM lists WHERE id=?", (item.get("list_id"),))
                    payload["list_name"] = list_row["name"] if list_row else "Lista de Compras"
                    self.sync.record("shopping_item", item["id"], "create", payload)
        elif result.type == "check_list_item" and isinstance(result.data, dict) and result.data.get("id"):
            payload = dict(result.data)
            list_row = self.db.one("SELECT name FROM lists WHERE id=?", (result.data.get("list_id"),))
            payload["list_name"] = list_row["name"] if list_row else "Lista de Compras"
            self.sync.record("shopping_item", result.data["id"], "complete", payload)

    def _refresh_synced_indexes(self) -> None:
        try:
            if self.obsidian_index:
                self.obsidian_index.index()
            self.knowledge_graph.rebuild()
            self.events.publish("sync", self.sync.summary() if self.sync else {})
        except Exception:
            self.logger.exception("Falha ao atualizar índices após sincronização")

    def close(self) -> None:
        if self.sync:
            self.sync.stop()
        if self.scheduler:
            self.scheduler.stop()
        try:
            self.ai.unload()
        except AttributeError:
            pass
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)
