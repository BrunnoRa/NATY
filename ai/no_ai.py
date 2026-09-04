from ai.base import AIProvider


class NoAIProvider(AIProvider):
    def is_available(self) -> bool: return False
    def load(self) -> None: return None
    def generate(self, prompt: str) -> str: raise RuntimeError("IA local está desativada.")
    def unload(self) -> None: return None
