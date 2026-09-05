from __future__ import annotations

from copy import deepcopy
import re
import threading
import time
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
        self._precision_generation = 0
        self._precision_snapshot = {
            "state": "IDLE", "active": False, "level": 0.0, "peak": 0.0,
            "expected": "", "transcription": "", "wer": None,
            "latency_ms": None, "error": None,
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

    @staticmethod
    def _word_error_rate(expected: str, actual: str) -> float | None:
        tokenize = lambda value: re.findall(r"[\wÀ-ÿ]+", value.casefold())
        reference, hypothesis = tokenize(expected), tokenize(actual)
        if not reference:
            return None
        previous = list(range(len(hypothesis) + 1))
        for index, reference_word in enumerate(reference, 1):
            current = [index]
            for position, hypothesis_word in enumerate(hypothesis, 1):
                current.append(min(
                    current[-1] + 1,
                    previous[position] + 1,
                    previous[position - 1] + (reference_word != hypothesis_word),
                ))
            previous = current
        return round(previous[-1] / len(reference), 4)

    def precision_snapshot(self) -> dict:
        with self._lock:
            result = deepcopy(self._precision_snapshot)
            result["microphone"] = deepcopy(self.manager.microphone)
            result["stt"] = type(self.manager.stt).__name__
            return result

    def _precision_update(self, generation: int, **changes) -> None:
        with self._lock:
            if generation == self._precision_generation:
                self._precision_snapshot.update(changes)

    def start_precision(self, expected: str) -> dict:
        if not self.settings.voice_enabled:
            with self._lock:
                self._precision_snapshot.update(
                    state="ERROR", active=False, error="O reconhecimento de voz está desativado."
                )
            return self.precision_snapshot()
        if self.snapshot()["active"]:
            self.stop()
        with self._lock:
            self._precision_generation += 1
            generation = self._precision_generation
            self._precision_snapshot = {
                "state": "LISTENING", "active": True, "level": 0.0, "peak": 0.0,
                "expected": expected.strip()[:500], "transcription": "", "wer": None,
                "latency_ms": None, "error": None,
            }
        started = time.perf_counter()

        def level(value: float) -> None:
            with self._lock:
                if generation != self._precision_generation:
                    return
                self._precision_snapshot["level"] = round(float(value), 5)
                self._precision_snapshot["peak"] = max(
                    float(self._precision_snapshot["peak"]), float(value)
                )

        def state(value: str) -> None:
            self._precision_update(generation, state=value.upper())

        def heard(text: str) -> None:
            latency = round((time.perf_counter() - started) * 1000, 2)
            self._precision_update(
                generation, state="COMPLETE", active=False, level=0.0,
                transcription=text, wer=self._word_error_rate(expected, text),
                latency_ms=latency,
            )

        def failed(message: str) -> None:
            self._precision_update(
                generation, state="ERROR", active=False, level=0.0, error=message
            )

        self.manager.listen_async(heard, failed, timeout=8.0, on_level=level, on_state=state)
        return self.precision_snapshot()

    def stop_precision(self) -> dict:
        with self._lock:
            self._precision_generation += 1
            self._precision_snapshot.update(state="IDLE", active=False, level=0.0)
        self.manager.stop_session()
        return self.precision_snapshot()

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
        self.stop_precision()
        self.stop()
        try: self.manager.tts.unload()
        except AttributeError: pass
