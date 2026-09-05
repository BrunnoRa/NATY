from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import inspect
import re
import threading
import time

from config import Settings
from voice.devices import friendly_audio_error, resolve_microphone
from voice.sapi_tts import SapiTTS
from voice.vosk_stt import VoskSTT
from voice.whisper_cpp import WhisperCppSTT
from voice.piper_tts import PiperTTS


def normalize_for_speech(text: str) -> str:
    """Remove formatação visual que deixa a leitura neural artificial."""
    value = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    value = re.sub(r"```.*?```", " trecho de código ", value, flags=re.DOTALL)
    value = re.sub(r"[`*_#>]", "", value)
    value = re.sub(r"(?m)^\s*[-•]\s+", "", value)
    return re.sub(r"\s+", " ", value).strip()


class SpeechChunker:
    """Mantém respostas comuns em um bloco e divide apenas textos longos."""

    def __init__(self, max_chars: int = 560):
        self.max_chars = max(240, max_chars)

    def chunks(self, text: str) -> list[str]:
        normalized = normalize_for_speech(text)
        if not normalized:
            return []
        if len(normalized) <= self.max_chars:
            return [normalized]
        units = [item.strip() for item in re.split(r"(?<=[.!?…])\s+", normalized) if item.strip()]
        result: list[str] = []
        current = ""
        for unit in units:
            if len(unit) > self.max_chars:
                if current:
                    result.append(current)
                    current = ""
                result.extend(unit[index:index + self.max_chars].strip()
                              for index in range(0, len(unit), self.max_chars))
            elif current and len(current) + len(unit) + 1 > self.max_chars:
                result.append(current)
                current = unit
            else:
                current = f"{current} {unit}".strip()
        if current:
            result.append(current)
        return result


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
        self.microphone = resolve_microphone(
            settings.microphone_device,
            getattr(settings, "microphone_name", ""),
            getattr(settings, "microphone_hostapi", ""),
            getattr(settings, "microphone_sample_rate", 0),
        )
        device_id = self.microphone["id"] if self.microphone else settings.microphone_device
        neural_tts = PiperTTS(getattr(settings, "piper_executable_path", ""), getattr(settings, "piper_model_path", ""),
                              getattr(settings, "piper_config_path", ""))
        self.tts = tts or (neural_tts if settings.tts_provider == "piper" and neural_tts.available()
                           else SapiTTS(settings.voice, settings.voice_rate, settings.voice_volume))
        whisper = WhisperCppSTT(settings.whisper_executable_path, settings.whisper_model_path,
            device=device_id, microphone_gain=settings.microphone_gain,
            automatic_gain=settings.automatic_gain_enabled, pre_roll_ms=settings.pre_roll_ms,
            end_silence_ms=settings.end_silence_ms, max_utterance_seconds=settings.max_utterance_seconds)
        self.stt = stt or (whisper if settings.stt_provider == "whisper_cpp" and whisper.available()
                           else VoskSTT(settings.vosk_model_path, unload_after_use=False,
                               device=device_id, microphone_gain=settings.microphone_gain,
                               automatic_gain=settings.automatic_gain_enabled))
        followup = max(5, min(15, int(settings.conversation_followup_seconds)))
        self.session = VoiceSession(followup)
        self.active = False
        self._lock = threading.Lock()
        self._speech_lock = threading.Lock()
        self._speech_generation = 0
        self._speech_chunker = SpeechChunker()

    def _speak_response(self, text: str) -> None:
        with self._speech_lock:
            self._speech_generation += 1
            generation = self._speech_generation
        for chunk in self._speech_chunker.chunks(text):
            with self._speech_lock:
                if generation != self._speech_generation: return
            self.tts.speak(chunk)

    def _listen_once(self, timeout: float, on_level=None, on_state=None) -> str:
        parameters = inspect.signature(self.stt.listen_once).parameters
        if "on_state" in parameters:
            return self.stt.listen_once(timeout, on_level=on_level, on_state=on_state)
        return self.stt.listen_once(timeout, on_level=on_level)

    def speak_async(self, text: str, on_done: Callable[[], None] | None = None) -> None:
        if not self.settings.tts_enabled:
            if on_done: on_done()
            return
        def work():
            try: self._speak_response(text)
            finally:
                if on_done: on_done()
        threading.Thread(target=work, name="NatyTTS", daemon=True).start()

    def listen_async(
        self,
        on_text: Callable[[str], None],
        on_error: Callable[[str], None],
        timeout: float = 8.0,
        on_level: Callable[[float], None] | None = None,
        on_state: Callable[[str], None] | None = None,
    ) -> None:
        def work():
            with self._lock:
                if self.active:
                    on_error("A Naty já está ouvindo.")
                    return
                self.active = True
            started = time.perf_counter()
            try:
                text = self._listen_once(timeout, on_level=on_level, on_state=on_state)
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
        on_state: Callable[[str], None] | None = None,
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

        self.listen_async(heard, failed, timeout=8.0, on_level=on_level, on_state=on_state)

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
                    self._speak_response(text)
                if not self.session.active:
                    on_closed(); return
                if on_state: on_state("listening")
                with self._lock:
                    if self.active:
                        raise RuntimeError("A Naty já está ouvindo.")
                    self.active = True
                started = time.perf_counter()
                followup = self._listen_once(self.session.followup_seconds, on_level=on_level, on_state=on_state)
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
        with self._speech_lock: self._speech_generation += 1
        try: self.tts.stop()
        except AttributeError: pass
        self._unload_if_configured()

    def _unload_if_configured(self) -> None:
        if self.settings.unload_stt_after_use:
            try: self.stt.unload()
            except AttributeError: pass

    @property
    def stt_loaded(self) -> bool: return getattr(self.stt, "_model", None) is not None


VoiceManager = VoiceSessionManager
