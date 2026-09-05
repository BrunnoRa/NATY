from core.models import Intent, RequestType
from nlu.parser import RuleParser
from nlu import intents
import unicodedata


class IntentRouter:
    def __init__(self, parser: RuleParser | None = None): self.parser = parser or RuleParser()

    def route(self, text: str) -> Intent:
        intent = self.parser.parse(text)
        intent.request_type = self._request_type(intent.name)
        plain = "".join(c for c in unicodedata.normalize("NFD", text.casefold()) if unicodedata.category(c) != "Mn")
        if intent.name == intents.UNKNOWN and ("lembre que" in plain or "lembra que" in plain or "o que voce lembra" in plain):
            intent.request_type = RequestType.MEMORY.value
        elif intent.name == intents.UNKNOWN and any(term in plain for term in ("estou cansado", "estou cansada", "dia foi cansativo")):
            intent.request_type = RequestType.CHAT.value
        return intent

    @staticmethod
    def _request_type(name: str) -> str:
        groups = {
            RequestType.CHAT: {intents.CHAT},
            RequestType.QUESTION: {intents.TIME_QUERY},
            RequestType.LOCAL_ACTION: {intents.ADD_LIST_ITEMS, intents.CHECK_LIST_ITEM, intents.REMOVE_LIST_ITEM, intents.CLEAR_CHECKED},
            RequestType.SEARCH: {intents.RESEARCH},
            RequestType.DEEP_RESEARCH: {intents.COMPARE},
            RequestType.PLANNING: {intents.SHOW_DAY, intents.NEXT_TASK, intents.PLAN_NOW, intents.PLAN_TIME},
            RequestType.TASK: {intents.CREATE_TASK, intents.LIST_TASKS, intents.COMPLETE_TASK, intents.COMPLETE_LAST, intents.UPDATE_LAST, intents.POSTPONE_LAST},
            RequestType.REMINDER: {intents.CREATE_REMINDER, intents.LIST_REMINDERS},
            RequestType.OPEN_APP: {intents.OPEN_APP},
            RequestType.MEDIA: {intents.MEDIA_CONTROL},
            RequestType.OBSIDIAN_QUERY: {intents.OBSIDIAN_QUERY},
            RequestType.AUTOMATION: {intents.CREATE_AUTOMATION},
            RequestType.DELEGATE: {intents.DELEGATE},
        }
        for kind, names in groups.items():
            if name in names:
                return kind.value
        if name == intents.UNKNOWN:
            return RequestType.CLARIFICATION.value
        return RequestType.MEMORY.value if name in {intents.CREATE_NOTE} else RequestType.LOCAL_ACTION.value
