from abc import ABC, abstractmethod


class STTProvider(ABC):
    @abstractmethod
    def available(self) -> bool: ...
    @abstractmethod
    def listen_once(self, timeout: float = 8.0) -> str: ...
    def unload(self) -> None: pass
