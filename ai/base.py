from __future__ import annotations

from abc import ABC, abstractmethod


class AIProvider(ABC):
    @abstractmethod
    def is_available(self) -> bool: ...
    @abstractmethod
    def load(self) -> None: ...
    @abstractmethod
    def generate(self, prompt: str) -> str: ...
    @abstractmethod
    def unload(self) -> None: ...
