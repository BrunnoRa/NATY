from __future__ import annotations

from copy import deepcopy
import threading
from typing import Callable

from config import Settings
from voice.manager import VoiceSessionManager


class VoiceController:
    """Coordena uma VoiceSession em background e expõe estado serializável ao IPC."""

    def __init__(self, settings: Settings, process_text: Callable[[str], dict], manager=None):
        self.settings = settings
        self.process_text = process_text
        self.manager = manager or VoiceSessionManager(settings)
        self._lock = threading.RLock()
        self._sequence = 0
        self._snapshot = {
            "state": "IDLE", "active": False, "level": 0.0, "peak": 0.0,
            "transcription": "", "response": "", "result": None, "error": None,
        }

    def snapshot(self) -> dict:
        with self._lock:
            result = deepcopy(self._snapshot)
            result["sequence"] = self._sequence
            result["microphone"] = deepcopy(self.manager.microphone)
            result["stt"] = type(self.manager.stt).__name__
            result["tts"] = type(self.manager.tts).__name__
            return result

    def _update(self, **changes) -> None:
        with self._lock:
            self._snapshot.update(changes)
            self._sequence += 1

    def _state(self, state: str) -> None:
        self._update(state=state.upper())

    def _level(self, value: float) -> None:
        with self._lock:
            self._snapshot["level"] = round(float(value), 5)
            self._snapshot["peak"] = max(float(self._snapshot["peak"]), float(value))
            self._sequence += 1

    def start(self) -> dict:
        if not self.settings.voice_enabled:
            self._update(state="ERROR", active=False, error="O reconhecimento de voz está desativado.")
            return self.snapshot()
        current = self.snapshot()
        if current["active"]:
            self.stop()
        self._update(state="LISTENING", active=True, level=0.0, peak=0.0,
                     transcription="", response="", result=None, error=None)
        self.manager.start_session(self._heard, self._failed, self._level, self._state)
        return self.snapshot()

    def _heard(self, text: str) -> None:
        self._update(state="PROCESSING", transcription=text, level=0.0)
        try:
            result = self.process_text(text)
            answer = str(result.get("text") or result.get("message") or "")
            panel = result.get("ui", {}).get("panel") if isinstance(result.get("ui"), dict) else None
            self._update(state="RETRIEVING" if panel in {"research", "project", "today"} else "PROCESSING",
                         response=answer, result=result)
            self.manager.respond_and_follow_up(
                answer, self._heard, self._failed, self._closed, self._state, self._level)
        except Exception as exc:
            self._failed(str(exc))

    def _closed(self) -> None:
        self._update(state="IDLE", active=False, level=0.0)

    def _failed(self, message: str) -> None:
        self._update(state="ERROR", active=False, level=0.0, error=message)

    def stop(self) -> dict:
        self.manager.stop_session()
        self._update(state="IDLE", active=False, level=0.0)
        return self.snapshot()

    def close(self) -> None:
        self.stop()
        try: self.manager.tts.unload()
        except AttributeError: pass
