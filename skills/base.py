from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from core.models import Intent, ToolResult


@dataclass(frozen=True, slots=True)
class SkillInfo:
    name: str
    description: str
    intents: tuple[str, ...]
    permissions: tuple[str, ...]


class Skill(ABC):
    info: SkillInfo
    @abstractmethod
    def execute(self, intent: Intent) -> ToolResult: ...
