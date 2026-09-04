from abc import ABC, abstractmethod


class WakeWordProvider(ABC):
    @abstractmethod
    def available(self) -> bool: ...
    @abstractmethod
    def start(self, callback) -> None: ...
    @abstractmethod
    def stop(self) -> None: ...


class DisabledWakeWord(WakeWordProvider):
    def available(self) -> bool: return False
    def start(self, callback) -> None: return None
    def stop(self) -> None: return None
