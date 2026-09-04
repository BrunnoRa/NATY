from __future__ import annotations

from core.models import AppState, ToolResult
from nlu import intents


class AgentRouter:
    def __init__(self, intent_router, skills, conversation, events):
        self.intent_router, self.skills, self.conversation, self.events = intent_router, skills, conversation, events

    def handle(self, text: str) -> tuple[ToolResult, str]:
        intent = self.intent_router.route(text)
        if intent.name == intents.UNKNOWN or self.conversation.context.state.get("pending_memory_delete"):
            self.events.publish("state", AppState.RETRIEVING)
            return self.conversation.respond(text), "conversation"
        if intent.name in {intents.RESEARCH, intents.COMPARE}: self.events.publish("state", AppState.RESEARCHING)
        if intent.name in {intents.CONNECT_GOOGLE, intents.DISCONNECT_GOOGLE, intents.GMAIL_SEARCH, intents.GMAIL_DRAFT, intents.GMAIL_SEND, intents.GOOGLE_CALENDAR_UPCOMING}:
            self.events.publish("state", AppState.GMAIL)
        return self.skills.execute(intent), intent.name
