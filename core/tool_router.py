from __future__ import annotations

from core.context import SessionContext
from core.models import Intent, ToolResult
from nlu import intents


class ToolRouter:
    def __init__(self, *, tasks, lists, reminders, projects, notes, calendar, planner, research, context: SessionContext,
                 google=None, automations=None, windows=None, planning=None, knowledge=None, system_status=None,
                 temporal_memory=None, briefing=None, workspaces=None, notifications=None):
        self.tasks, self.lists, self.reminders = tasks, lists, reminders
        self.projects, self.notes, self.calendar, self.planner, self.research = projects, notes, calendar, planner, research
        self.context = context
        self.google = google
        self.automations, self.windows, self.planning, self.knowledge = automations, windows, planning, knowledge
        self.system_status = system_status
        self.temporal_memory = temporal_memory
        self.briefing = briefing
        self.workspaces = workspaces
        self.notifications = notifications
        self.active_context = None
        self.pending_confirmation: tuple[str, dict] | None = None

    def execute(self, intent: Intent) -> ToolResult:
        e, name = intent.entities, intent.name
        last = self.context.last_entity
        if name == intents.CANCEL:
            self.pending_confirmation = None
            return ToolResult(True, "Cancelado.")
        if name == intents.CONFIRM:
            if not self.pending_confirmation: return ToolResult(False, "Não há nenhuma ação aguardando confirmação.")
            action, _ = self.pending_confirmation; self.pending_confirmation = None
            if action == "delete_all_tasks":
                count = self.tasks.repo.delete_all()
                return ToolResult(True, f"Apaguei {count} tarefa(s).")
            if action == "gmail_send" and self.google:
                return self.google.send_last_draft(confirmed=True)
            if action == "disconnect_google" and self.google:
                return self.google.disconnect(confirmed=True)
        if name == intents.DELETE_ALL_TASKS:
            self.pending_confirmation = ("delete_all_tasks", {})
            return ToolResult(False, "Isso apagará todas as tarefas. Diga 'sim' para confirmar ou 'cancelar'.")
        if name == intents.CONNECT_GOOGLE and self.google: return self.google.connect()
        if name == intents.DISCONNECT_GOOGLE and self.google:
            self.pending_confirmation = ("disconnect_google", {})
            return ToolResult(False, "Isso removerá o token Google local. Diga 'sim' para confirmar ou 'cancelar'.")
        if name == intents.GMAIL_SEARCH and self.google: return self.google.search_mail(e.get("query", "in:inbox"))
        if name == intents.GMAIL_DRAFT and self.google: return self.google.draft(e.get("to", ""), e.get("subject", "Mensagem da Naty"), e.get("body", ""))
        if name == intents.GMAIL_SEND and self.google:
            if not self.google.last_draft_id: return ToolResult(False, "Não há rascunho recente para enviar.")
            self.pending_confirmation = ("gmail_send", {})
            return ToolResult(False, "Isso enviará o rascunho pelo Gmail. Diga 'sim' para confirmar ou 'cancelar'.")
        if name == intents.GOOGLE_CALENDAR_UPCOMING and self.google: return self.google.upcoming()
        if name == intents.GOOGLE_CALENDAR_FREE and self.google: return self.google.is_free(e.get("starts_at"))
        if name == intents.CREATE_TASK: return self.tasks.create(**e)
        if name == intents.LIST_TASKS: return self.tasks.list_pending()
        if name == intents.COMPLETE_TASK: return self.tasks.complete_named(e["query"])
        if name == intents.COMPLETE_LAST:
            if not last or last.type != "task": return ToolResult(False, "Qual tarefa você concluiu?")
            return self.tasks.complete(last.id)
        if name == intents.UPDATE_LAST:
            if not last or last.type != "task": return ToolResult(False, "A qual tarefa você se refere?")
            return self.tasks.update(last.id, **e)
        if name == intents.POSTPONE_LAST:
            if not last or last.type != "task": return ToolResult(False, "Qual tarefa devo remarcar?")
            if not e.get("due_at"): return ToolResult(False, "Para quando devo remarcar?")
            return self.tasks.postpone(last.id, e["due_at"])
        if name == intents.CREATE_REMINDER: return self.reminders.create(**e)
        if name == intents.LIST_REMINDERS: return self.reminders.list_pending()
        if name == intents.CREATE_APPOINTMENT:
            if self.google and self.google.settings.google_enabled:
                return self.google.create_event(e.get("title", "Compromisso"), e.get("starts_at"), e.get("ends_at"))
            return self.calendar.create(**e)
        if name == intents.LIST_APPOINTMENTS: return self.calendar.today()
        if name == intents.CREATE_LIST: return self.lists.create(e["name"])
        if name == intents.ADD_LIST_ITEMS: return self.lists.add(e.get("list_name") or "Lista de Compras", e["items"], self.context.last_list_id)
        if name == intents.SHOW_LIST: return self.lists.show(e.get("list_name"), self.context.last_list_id, e.get("unchecked_only", False))
        if name == intents.CHECK_LIST_ITEM: return self.lists.check(e.get("list_name"), e["item"], self.context.last_list_id)
        if name == intents.REMOVE_LIST_ITEM: return self.lists.remove(e.get("list_name"), e["item"], self.context.last_list_id)
        if name == intents.CLEAR_CHECKED: return self.lists.clear_checked(e.get("list_name"), self.context.last_list_id)
        if name == intents.CREATE_PROJECT: return self.projects.create(e["name"])
        if name == intents.PROJECT_OVERDUE: return self.projects.overdue(e["name"])
        if name == intents.CREATE_NOTE:
            project_id = None
            if e.get("project"):
                project = self.projects.repo.find(e["project"]) or self.projects.repo.create(e["project"])
                project_id = project["id"]
            return self.notes.create("Nota da Naty", e["content"], project_id)
        if name == intents.PLAN_TIME: return self.planner.suggest(e["minutes"])
        if name == intents.PLAN_NOW: return self.planner.suggest()
        if name == intents.SHOW_DAY and self.planning: return self.planning.show_day(e.get("day", "today"))
        if name == intents.NEXT_TASK and self.planning: return self.planning.next_task()
        if name == intents.TIME_QUERY:
            from datetime import datetime
            now = datetime.now().astimezone()
            return ToolResult(True, f"Agora são {now:%H:%M}.", {"time": now.isoformat(timespec="seconds")}, type="current_time")
        if name in {intents.SYSTEM_STATUS, intents.SYSTEM_DIAGNOSIS} and self.system_status:
            return self.system_status.status(e.get("focus", "general"), diagnose=name == intents.SYSTEM_DIAGNOSIS)
        if name == intents.TEMPORAL_RECALL and self.temporal_memory:
            return self.temporal_memory.recall(e.get("kind", "where_stopped"))
        if name == intents.DAILY_BRIEFING and self.briefing:
            return self.briefing.build()
        if name == intents.WORKSPACE_CREATE and self.workspaces: return self.workspaces.create(e.get("name", ""))
        if name == intents.WORKSPACE_CONFIGURE and self.workspaces: return self.workspaces.configure_apps(e.get("name", ""), e.get("apps", []))
        if name == intents.WORKSPACE_ACTIVATE and self.workspaces: return self.workspaces.activate(e.get("name", ""))
        if name == intents.WORKSPACE_END and self.workspaces: return self.workspaces.end(e.get("name", ""))
        if name == intents.WORKSPACE_LIST and self.workspaces: return self.workspaces.list()
        if name == intents.NOTIFICATION_LIST and self.notifications:
            return self.notifications.show(bool(e.get("important_only")))
        if name == intents.ACTIVE_CONTEXT_STATUS and self.active_context: return self.active_context.show()
        if name == intents.ACTIVE_CONTEXT_RETURN and self.active_context: return self.active_context.return_to_previous()
        if name == intents.ACTIVE_CONTEXT_PROJECT and self.active_context: return self.active_context.return_to_previous(project_only=True)
        if name == intents.OBSIDIAN_QUERY and self.knowledge: return self.knowledge.query(e.get("query", ""))
        if name == intents.CREATE_AUTOMATION and self.automations: return self.automations.create(**e)
        if name == intents.OPEN_APP and self.windows: return self.windows.open_app(e["app"])
        if name == intents.MEDIA_CONTROL and self.windows: return self.windows.media(e["action"])
        if name == intents.DELEGATE and self.windows: return self.windows.delegate(e.get("query", intent.raw_text))
        if name in {intents.RESEARCH, intents.COMPARE}: return self.research.search(e["query"], compare=name == intents.COMPARE, read_pages=name == intents.COMPARE)
        if name == intents.SAVE_RESEARCH: return self.research.save_last_to_obsidian()
        if name == intents.OPEN_RESEARCH_BROWSER: return self.research.open_last_in_browser()
        if name == intents.HELP:
            return ToolResult(True, "Posso criar e acompanhar tarefas, lembretes, listas, projetos e notas; planejar seu tempo; recuperar contexto do Obsidian; pesquisar na internet; e, se você autorizar, consultar Gmail e Google Calendar.")
        return ToolResult(False, "Não entendi esse pedido. Tente, por exemplo: 'cria tarefa entregar relatório sexta'.")
