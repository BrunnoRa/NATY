from __future__ import annotations

from core.models import Intent, ToolResult
from skills.base import Skill, SkillInfo


class RoutedSkill(Skill):
    def __init__(self, info: SkillInfo, executor): self.info, self.executor = info, executor
    def execute(self, intent: Intent) -> ToolResult: return self.executor(intent)


class SkillRegistry:
    def __init__(self): self._by_intent: dict[str, Skill] = {}; self._skills: dict[str, Skill] = {}
    def register(self, skill: Skill) -> None:
        self._skills[skill.info.name] = skill
        for intent in skill.info.intents:
            if intent in self._by_intent: raise ValueError(f"Intent duplicada: {intent}")
            self._by_intent[intent] = skill
    def execute(self, intent: Intent) -> ToolResult:
        skill = self._by_intent.get(intent.name)
        if not skill: return ToolResult(False, "Nenhuma skill permitida corresponde a esse pedido.")
        return skill.execute(intent)
    def status(self) -> list[dict]:
        return [{
            "name": s.info.name, "description": s.info.description, "category": s.info.category,
            "aliases": s.info.aliases, "permissions": s.info.permissions, "intents": s.info.intents,
            "requires_network": s.info.requires_network, "requires_confirmation": s.info.requires_confirmation,
            "requires_credentials": s.info.requires_credentials, "ui_panel": s.info.ui_panel,
            "examples": s.info.examples,
        } for s in self._skills.values()]

    def suggestions(self, limit: int = 4) -> list[str]:
        preferred = ("briefing", "temporal_memory", "system_status", "workspaces", "clipboard")
        examples = [self._skills[name].info.examples[0] for name in preferred
                    if name in self._skills and self._skills[name].info.examples]
        return examples[:max(0, limit)]


def build_registry(tool_router) -> SkillRegistry:
    from nlu import intents as i
    groups = {
        "tasks": ((i.CREATE_TASK,i.LIST_TASKS,i.COMPLETE_TASK,i.COMPLETE_LAST,i.UPDATE_LAST,i.POSTPONE_LAST,i.DELETE_ALL_TASKS,i.CONFIRM,i.CANCEL), ("sqlite:tasks",)),
        "lists": ((i.CREATE_LIST,i.ADD_LIST_ITEMS,i.SHOW_LIST,i.CHECK_LIST_ITEM,i.REMOVE_LIST_ITEM,i.CLEAR_CHECKED), ("sqlite:lists","obsidian:write-managed")),
        "reminders": ((i.CREATE_REMINDER,i.LIST_REMINDERS), ("sqlite:reminders",)),
        "automations": ((i.CREATE_AUTOMATION,), ("sqlite:automations", "notify")),
        "calendar": ((i.CREATE_APPOINTMENT,i.LIST_APPOINTMENTS), ("sqlite:calendar",)),
        "planning": ((i.SHOW_DAY,i.NEXT_TASK,i.PLAN_NOW,i.PLAN_TIME,i.TIME_QUERY), ("sqlite:read",)),
        "knowledge": ((i.OBSIDIAN_QUERY,), ("obsidian:read-managed", "sqlite:fts5")),
        "windows": ((i.OPEN_APP,i.MEDIA_CONTROL,i.DELEGATE), ("windows:allowlist",)),
        "projects": ((i.CREATE_PROJECT,i.PROJECT_OVERDUE,i.CREATE_NOTE), ("sqlite:projects","obsidian:write-managed")),
        "research": ((i.RESEARCH,i.COMPARE,i.SAVE_RESEARCH,i.OPEN_RESEARCH_BROWSER), ("network:search","obsidian:write-managed")),
        "help": ((i.HELP,), ("none",)),
        "system_status": ((i.SYSTEM_STATUS,i.SYSTEM_DIAGNOSIS), ("system:read",)),
        "temporal_memory": ((i.TEMPORAL_RECALL,), ("sqlite:activity-read",)),
        "briefing": ((i.DAILY_BRIEFING,), ("sqlite:read", "google:optional")),
        "workspaces": ((i.WORKSPACE_CREATE,i.WORKSPACE_CONFIGURE,i.WORKSPACE_ACTIVATE,i.WORKSPACE_END,i.WORKSPACE_LIST), ("sqlite:workspaces", "windows:allowlist")),
        "notifications": ((i.NOTIFICATION_LIST,), ("sqlite:notifications-read",)),
        "active_context": ((i.ACTIVE_CONTEXT_STATUS,i.ACTIVE_CONTEXT_RETURN,i.ACTIVE_CONTEXT_PROJECT), ("windows:active-window-metadata",)),
        "clipboard": ((i.CLIPBOARD_SHOW,i.CLIPBOARD_SUMMARIZE,i.CLIPBOARD_RESEARCH,i.CLIPBOARD_SAVE), ("windows:clipboard-explicit",)),
        "safe_files": ((i.FILE_OPEN_FOLDER,i.FILE_FIND,i.FILE_RECENT,i.FILE_OPEN_LAST,i.FILE_DELETE), ("filesystem:configured-roots", "confirmation:delete")),
        "google_workspace": ((i.CONNECT_GOOGLE,i.DISCONNECT_GOOGLE,i.GMAIL_SEARCH,i.GMAIL_DRAFT,i.GMAIL_SEND,i.GOOGLE_CALENDAR_UPCOMING,i.GOOGLE_CALENDAR_FREE), ("oauth:google","gmail:scoped","calendar:scoped")),
    }
    registry = SkillRegistry()
    metadata = {
        "tasks": ("Organiza e acompanha tarefas.", "PRODUCTIVITY", ("tarefas",), False, False, False, "today", ("Mostra minhas tarefas",)),
        "lists": ("Gerencia listas locais e sincroniza listas gerenciadas.", "PRODUCTIVITY", ("listas", "compras"), False, False, False, "shopping", ("Mostra minha lista de compras",)),
        "reminders": ("Cria e consulta lembretes locais.", "PRODUCTIVITY", ("lembretes",), False, False, False, "today", ("Cria um lembrete para amanhã",)),
        "automations": ("Cria rotinas locais permitidas.", "AUTOMATION", ("rotinas",), False, False, False, "automation", ("Cria um lembrete recorrente",)),
        "calendar": ("Gerencia compromissos locais.", "PRODUCTIVITY", ("agenda",), False, False, False, "today", ("O que tenho na agenda?",)),
        "planning": ("Planeja o dia e sugere a próxima tarefa.", "PRODUCTIVITY", ("planejamento",), False, False, False, "today", ("O que faço agora?",)),
        "knowledge": ("Consulta conhecimento indexado no Obsidian.", "MEMORY", ("obsidian", "memória"), False, False, False, "project", ("O que você sabe sobre a NATY?",)),
        "windows": ("Abre aplicativos permitidos e controla mídia.", "WINDOWS", ("launcher", "mídia"), False, False, False, "none", ("Abre o Spotify",)),
        "projects": ("Organiza projetos e notas locais.", "PRODUCTIVITY", ("projetos",), False, False, False, "project", ("Cria um projeto chamado Pesquisa",)),
        "research": ("Pesquisa na web mantendo fontes.", "RESEARCH", ("pesquisa", "web"), True, False, False, "research", ("Pesquisa as notícias sobre Python",)),
        "help": ("Explica capacidades e estado da própria NATY.", "CORE", ("ajuda", "capacidades"), False, False, False, "capabilities", ("O que você sabe fazer?",)),
        "system_status": ("Consulta e diagnostica o estado do computador.", "SYSTEM", ("sistema", "computador"), False, False, False, "system", ("Como está meu computador?",)),
        "temporal_memory": ("Recupera atividades úteis e o ponto de retomada.", "MEMORY", ("onde paramos",), False, False, False, "timeline", ("Onde paramos?",)),
        "briefing": ("Resume compromissos e prioridades do dia.", "PRODUCTIVITY", ("briefing",), False, False, False, "briefing", ("Como está meu dia?",)),
        "workspaces": ("Configura e ativa modos seguros de trabalho.", "AUTOMATION", ("modos", "workspaces"), False, False, False, "workspace", ("Quais modos eu tenho?",)),
        "notifications": ("Agrupa alertas emitidos pela própria NATY.", "CORE", ("notificações",), False, False, False, "notifications", ("Tem algo importante?",)),
        "active_context": ("Identifica e reativa a última janela usada na sessão.", "CONTEXT", ("aplicativo ativo", "contexto"), False, False, False, "active_context", ("Em que programa eu estou?",)),
        "clipboard": ("Lê texto do Clipboard somente sob comando.", "CONTEXT", ("clipboard", "área de transferência"), False, False, False, "clipboard", ("Resume o que eu copiei",)),
        "safe_files": ("Encontra e abre arquivos em raízes permitidas.", "WINDOWS", ("arquivos", "pastas"), False, True, False, "files", ("Encontra o arquivo relatório",)),
        "google_workspace": ("Consulta Gmail e Google Calendar com OAuth.", "COMMUNICATION", ("gmail", "google", "agenda google"), True, True, True, "gmail", ("Mostra meus próximos compromissos",)),
    }
    for name, (names, permissions) in groups.items():
        description, category, aliases, network, confirmation, credentials, panel, examples = metadata[name]
        registry.register(RoutedSkill(SkillInfo(name, description, tuple(names), tuple(permissions), category, aliases,
                                                 network, confirmation, credentials, panel, examples), tool_router.execute))
    return registry
