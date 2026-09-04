from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class Risk(str, Enum):
    READ = "read"
    DRAFT = "draft"
    WRITE = "write"
    DESTRUCTIVE = "destructive"


@dataclass(frozen=True, slots=True)
class ConnectorInfo:
    name: str
    permissions: tuple[str, ...]
    optional: bool = True


class Connector(ABC):
    info: ConnectorInfo

    @abstractmethod
    def available(self) -> bool: ...


class ConfirmationRequired(PermissionError):
    pass


def require_confirmation(confirmed: bool, action: str) -> None:
    if not confirmed:
        raise ConfirmationRequired(f"Confirmação explícita necessária para {action}.")
