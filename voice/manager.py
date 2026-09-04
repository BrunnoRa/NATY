from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import threading
import time

from config import Settings
from voice.devices import friendly_audio_error
from voice.sapi_tts import SapiTTS
from voice.vosk_stt import VoskSTT


@dataclass(slots=True)
class VoiceSession:
    followup_seconds: int = 8
    active: bool = False
    turns: int = 0
    started_at: float | None = None
    last_transcription: str = ""
    last_latency_ms: float | None = None
    generation: int = 0

    def open(self) -> None:
        self.generation += 1
        self.active = True
        self.turns = 0
        self.started_at = time.monotonic()
        self.last_transcription = ""
        self.last_latency_ms = None

    def record(self, text: str, latency_ms: float | None = None) -> None:
        self.turns += 1
        self.last_transcription = text
        self.last_latency_ms = latency_ms

    def close(self) -> None:
        self.active = False
        self.generation += 1


class VoiceSessionManager:
    def __init__(self, settings: Settings, stt=None, tts=None):
        self.settings = settings
        self.tts = tts or SapiTTS(settings.voice, settings.voice_rate, settings.voice_volume)
        self.stt = stt or VoskSTT(settings.vosk_model_path, unload_after_use=False,
                                  device=settings.microphone_device, microphone_gain=settings.microphone_gain,
                                  automatic_gain=settings.automatic_gain_enabled)
        followup = max(5, min(15, int(settings.conversation_followup_seconds)))
        self.session = VoiceSession(followup)
        self.active = False
        self._lock = threading.Lock()

    def speak_async(self, text: str, on_done: Callable[[], None] | None = None) -> None:
        if not self.settings.tts_enabled:
            if on_done: on_done()
            return
        def work():
            try: self.tts.speak(text)
            finally:
                if on_done: on_done()
        threading.Thread(target=work, name="NatyTTS", daemon=True).start()

    def listen_async(
        self,
        on_text: Callable[[str], None],
        on_error: Callable[[str], None],
        timeout: float = 8.0,
        on_level: Callable[[float], None] | None = None,
    ) -> None:
        def work():
            with self._lock:
                if self.active:
                    on_error("A Naty já está ouvindo.")
                    return
                self.active = True
            started = time.perf_counter()
            try:
                text = self.stt.listen_once(timeout, on_level=on_level)
                latency = (time.perf_counter() - started) * 1000
                if not text:
                    with self._lock: self.active = False
                    on_error("Não detectei fala inteligível. Verifique o nível do microfone e tente falar mais perto.")
                else:
                    if self.session.active: self.session.record(text, latency)
                    with self._lock: self.active = False
                    on_text(text)
            except Exception as exc:
                with self._lock: self.active = False
                on_error(friendly_audio_error(exc))
            finally:
                with self._lock: self.active = False
        threading.Thread(target=work, name="NatySTT", daemon=True).start()

    def start_session(
        self,
        on_text: Callable[[str], None],
        on_error: Callable[[str], None],
        on_level: Callable[[float], None] | None = None,
    ) -> None:
        self.session.open()
        generation = self.session.generation

        def heard(text: str) -> None:
            if self.session.active and self.session.generation == generation:
                on_text(text)

        def failed(message: str) -> None:
            if self.session.generation == generation:
                self.session.close()
                self._unload_if_configured()
                on_error(message)

        self.listen_async(heard, failed, timeout=8.0, on_level=on_level)

    def respond_and_follow_up(
        self,
        text: str,
        on_text: Callable[[str], None],
        on_error: Callable[[str], None],
        on_closed: Callable[[], None],
        on_state: Callable[[str], None] | None = None,
        on_level: Callable[[float], None] | None = None,
    ) -> None:
        generation = self.session.generation
        def work() -> None:
            try:
                if self.settings.tts_enabled:
                    if on_state: on_state("speaking")
                    self.tts.speak(text)
                if not self.session.active:
                    on_closed(); return
                if on_state: on_state("listening")
                with self._lock:
                    if self.active:
                        raise RuntimeError("A Naty já está ouvindo.")
                    self.active = True
                started = time.perf_counter()
                followup = self.stt.listen_once(self.session.followup_seconds, on_level=on_level)
                latency = (time.perf_counter() - started) * 1000
                with self._lock: self.active = False
                if not self.session.active or self.session.generation != generation:
                    on_closed()
                elif followup:
                    self.session.record(followup, latency)
                    on_text(followup)
                else:
                    self.session.close()
                    self._unload_if_configured()
                    on_closed()
            except Exception as exc:
                self.session.close()
                self._unload_if_configured()
                on_error(friendly_audio_error(exc))
            finally:
                with self._lock: self.active = False
        threading.Thread(target=work, name="NatyVoiceFollowup", daemon=True).start()

    def stop_session(self) -> None:
        self.session.close()
        self._unload_if_configured()

    def _unload_if_configured(self) -> None:
        if self.settings.unload_stt_after_use:
            try: self.stt.unload()
            except AttributeError: pass

    @property
    def stt_loaded(self) -> bool: return getattr(self.stt, "_model", None) is not None


VoiceManager = VoiceSessionManager
