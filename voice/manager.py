from __future__ import annotations

import threading
from collections.abc import Callable

from config import Settings
from voice.sapi_tts import SapiTTS
from voice.vosk_stt import VoskSTT


class VoiceSessionManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.tts = SapiTTS(settings.voice, settings.voice_rate, settings.voice_volume)
        self.stt = VoskSTT(settings.vosk_model_path, unload_after_use=settings.unload_stt_after_use, device=settings.microphone_device)
        self.active = False

    def speak_async(self, text: str, on_done: Callable[[], None] | None = None) -> None:
        if not self.settings.tts_enabled: return
        def work():
            try: self.tts.speak(text)
            finally:
                if on_done: on_done()
        threading.Thread(target=work, name="NatyTTS", daemon=True).start()

    def listen_async(self, on_text: Callable[[str], None], on_error: Callable[[str], None], timeout: float = 8.0) -> None:
        def work():
            self.active = True
            try:
                text = self.stt.listen_once(timeout)
                if not text: on_error("Não consegui compreender o áudio. Tente falar mais perto do microfone.")
                else: on_text(text)
            except Exception as exc:
                message = str(exc)
                lowered = message.lower()
                if "device" in lowered or "microphone" in lowered: message = "O microfone está indisponível ou ocupado."
                on_error(message)
            finally: self.active = False
        threading.Thread(target=work, name="NatySTT", daemon=True).start()

    @property
    def stt_loaded(self) -> bool: return self.stt._model is not None


VoiceManager = VoiceSessionManager
