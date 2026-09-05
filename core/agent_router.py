from __future__ import annotations

from core.models import AppState, ToolResult
from nlu import intents


class AgentRouter:
    def __init__(self, intent_router, skills, conversation, events):
        self.intent_router, self.skills, self.conversation, self.events = intent_router, skills, conversation, events

    def handle(self, text: str) -> tuple[ToolResult, str]:
        intent = self.intent_router.route(text)
        if intent.name in {intents.UNKNOWN, intents.CHAT} or self.conversation.context.state.get("pending_memory_delete"):
            self.events.publish("state", AppState.RETRIEVING)
            result = self.conversation.respond(text)
            return self._decorate(result, intent.name), intent.request_type
        if intent.name in {intents.RESEARCH, intents.COMPARE}: self.events.publish("state", AppState.RESEARCHING)
        if intent.name in {intents.CONNECT_GOOGLE, intents.DISCONNECT_GOOGLE, intents.GMAIL_SEARCH, intents.GMAIL_DRAFT, intents.GMAIL_SEND, intents.GOOGLE_CALENDAR_UPCOMING}:
            self.events.publish("state", AppState.GMAIL)
        return self._decorate(self.skills.execute(intent), intent.name), intent.request_type

    @staticmethod
    def _decorate(result: ToolResult, intent_name: str) -> ToolResult:
        graph_terms = {
            intents.SYSTEM_STATUS: ("Sistema",), intents.SYSTEM_DIAGNOSIS: ("Sistema",),
            intents.WORKSPACE_ACTIVATE: ("Workspace",), intents.WORKSPACE_LIST: ("Workspace",),
            intents.RESEARCH: ("Pesquisa", "Web"), intents.COMPARE: ("Pesquisa", "Web"),
            intents.OBSIDIAN_QUERY: ("Obsidian",), intents.GMAIL_SEARCH: ("Gmail",),
            intents.GOOGLE_CALENDAR_UPCOMING: ("Agenda",), intents.DAILY_BRIEFING: ("Briefing", "Agenda"),
            intents.CLIPBOARD_SHOW: ("Clipboard",), intents.CLIPBOARD_SUMMARIZE: ("Clipboard",),
        }.get(intent_name, ())
        if graph_terms and isinstance(result.data, dict): result.data["_graph_terms"] = graph_terms
        panels = {
            intents.RESEARCH: ("context", "research", "Pesquisa"),
            intents.COMPARE: ("context", "research", "Comparação"),
            intents.OBSIDIAN_QUERY: ("context", "project", "Memória"),
            intents.SHOW_DAY: ("context", "today", "Hoje"),
            intents.LIST_TASKS: ("context", "today", "Tarefas"),
            intents.NEXT_TASK: ("context", "today", "Próxima tarefa"),
            intents.SHOW_LIST: ("context", "shopping", "Lista"),
            intents.CREATE_AUTOMATION: ("context", "automation", "Automação"),
            intents.GMAIL_SEARCH: ("context", "gmail", "Gmail"),
            intents.GOOGLE_CALENDAR_UPCOMING: ("context", "today", "Agenda"),
            intents.WORKSPACE_LIST: ("context", "workspace", "Modos"),
            intents.WORKSPACE_ACTIVATE: ("context", "workspace", "Modo ativo"),
        }
        if intent_name in panels:
            mode, panel, title = panels[intent_name]
            result.ui_hint = {"mode": mode, "panel": panel, "title": title}
        if result.type == "message":
            result.type = intent_name
        return result
