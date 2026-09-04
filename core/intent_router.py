from core.models import Intent
from nlu.parser import RuleParser


class IntentRouter:
    def __init__(self, parser: RuleParser | None = None): self.parser = parser or RuleParser()
    def route(self, text: str) -> Intent: return self.parser.parse(text)
