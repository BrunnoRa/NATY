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
        return [{"name": s.info.name, "permissions": s.info.permissions, "intents": s.info.intents} for s in self._skills.values()]


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
        "google_workspace": ((i.CONNECT_GOOGLE,i.DISCONNECT_GOOGLE,i.GMAIL_SEARCH,i.GMAIL_DRAFT,i.GMAIL_SEND,i.GOOGLE_CALENDAR_UPCOMING,i.GOOGLE_CALENDAR_FREE), ("oauth:google","gmail:scoped","calendar:scoped")),
    }
    registry = SkillRegistry()
    for name, (names, permissions) in groups.items():
        registry.register(RoutedSkill(SkillInfo(name, f"Skill {name} da Naty", tuple(names), tuple(permissions)), tool_router.execute))
    return registry
