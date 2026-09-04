from __future__ import annotations

from collections.abc import Callable

from connectors.base import Connector


class ConnectorRegistry:
    """Closed lazy registry; factories run only when a named connector is requested."""

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], Connector]] = {}
        self._instances: dict[str, Connector] = {}

    def register(self, name: str, factory: Callable[[], Connector]) -> None:
        if name in self._factories:
            raise ValueError(f"Conector duplicado: {name}")
        self._factories[name] = factory

    def get(self, name: str) -> Connector:
        if name not in self._factories:
            raise KeyError(f"Conector não registrado: {name}")
        if name not in self._instances:
            self._instances[name] = self._factories[name]()
        return self._instances[name]

    def status(self) -> list[dict]:
        return [
            {"name": name, "loaded": name in self._instances,
             "available": self._instances[name].available() if name in self._instances else None}
            for name in self._factories
        ]
