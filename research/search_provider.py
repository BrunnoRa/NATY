from __future__ import annotations

from abc import ABC, abstractmethod
from core.models import ResearchItem


class SearchProvider(ABC):
    @abstractmethod
    def available(self) -> bool: ...
    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> list[ResearchItem]: ...
    def news(self, query: str, max_results: int = 5) -> list[ResearchItem]:
        return self.search(query, max_results)


# Nome arquitetural da V2; o alias mantém plugins e testes da V1 compatíveis.
ResearchProvider = SearchProvider
