from abc import ABC, abstractmethod


class TTSProvider(ABC):
    @abstractmethod
    def available(self) -> bool: ...
    @abstractmethod
    def speak(self, text: str) -> None: ...
    def stop(self) -> None: pass
    def unload(self) -> None: pass
