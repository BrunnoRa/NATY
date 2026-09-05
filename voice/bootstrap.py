from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from config import Settings
from voice.devices import list_microphones, resolve_microphone
from voice.piper_setup import diagnostics as piper_diagnostics, install_piper
from voice.sapi_tts import SapiTTS
from voice.whisper_setup import diagnostics as whisper_diagnostics, install_whisper


READY = "READY"
STT_MISSING = "STT_MISSING"
TTS_MISSING = "TTS_MISSING"
MIC_MISSING = "MIC_MISSING"
NEEDS_SETUP = "NEEDS_SETUP"
ERROR = "ERROR"


@dataclass(slots=True)
class VoiceBootstrapService:
    """Diagnostica e configura o pipeline de voz sem exigir scripts manuais."""

    settings: Settings

    def detect_microphones(self) -> list[dict]:
        return list_microphones()

    def _tts_status(self) -> dict:
        if self.settings.tts_provider == "piper":
            return piper_diagnostics(
                self.settings.piper_executable_path,
                self.settings.piper_model_path,
                self.settings.piper_config_path,
            )
        ready = SapiTTS().available()
        return {
            "ready": ready,
            "status": "Voz do Windows pronta." if ready else "Voz do Windows indisponível.",
            "provider": "Windows SAPI",
        }

    def diagnose(self) -> dict:
        try:
            microphones = self.detect_microphones()
            microphone = resolve_microphone(
                self.settings.microphone_device,
                self.settings.microphone_name,
                self.settings.microphone_hostapi,
                self.settings.microphone_sample_rate,
            )
            stt = whisper_diagnostics(
                self.settings.whisper_executable_path,
                self.settings.whisper_model_path,
            )
            tts = self._tts_status()
            missing = []
            if not stt["ready"]:
                missing.append("stt")
            if not tts["ready"]:
                missing.append("tts")
            if not microphone:
                missing.append("microphone")

            if not missing:
                state, reason, message = READY, None, "Voz pronta para uso."
            elif len(missing) > 1:
                state, reason, message = NEEDS_SETUP, "voice_incomplete", "Configuração de voz incompleta."
            elif missing[0] == "stt":
                state, reason, message = STT_MISSING, "whisper_missing", "Whisper Base precisa ser instalado."
            elif missing[0] == "tts":
                state, reason, message = TTS_MISSING, "tts_missing", "A voz de resposta precisa ser configurada."
            else:
                state, reason, message = MIC_MISSING, "microphone_missing", "Nenhum microfone foi encontrado."

            return {
                "state": state,
                "ready": state == READY,
                "reason": reason,
                "message": message,
                "stt": stt,
                "tts": tts,
                "microphones": microphones,
                "microphone": microphone,
            }
        except Exception as exc:
            return {
                "state": ERROR,
                "ready": False,
                "reason": "diagnostics_error",
                "message": "Não foi possível verificar a configuração de voz.",
                "error": str(exc),
                "stt": {"ready": False},
                "tts": {"ready": False},
                "microphones": [],
                "microphone": None,
            }

    def status(self) -> dict:
        return self.diagnose()

    def install_stt(self, progress: Callable | None = None) -> dict:
        install_whisper(self.settings, progress=progress)
        return self.status()

    def install_tts(self, progress: Callable | None = None) -> dict:
        install_piper(self.settings, progress=progress)
        return self.status()

    def configure_microphone(self, device_id: int) -> dict:
        selected = next((item for item in self.detect_microphones() if item["id"] == device_id), None)
        if selected is None:
            raise ValueError("O microfone selecionado não está disponível.")
        self.settings.microphone_device = selected["id"]
        self.settings.microphone_name = selected["name"]
        self.settings.microphone_hostapi = selected.get("hostapi", "")
        self.settings.microphone_sample_rate = int(selected.get("default_samplerate", 0))
        self.settings.save()
        return self.status()

    def repair(self, component: str = "all", progress: Callable | None = None) -> dict:
        if component not in {"all", "stt", "tts"}:
            raise ValueError("Componente de voz inválido.")
        current = self.status()
        if component in {"all", "stt"} and (component == "stt" or not current["stt"]["ready"]):
            install_whisper(self.settings, progress=progress)
        if component in {"all", "tts"} and self.settings.tts_provider == "piper" and (
            component == "tts" or not current["tts"]["ready"]
        ):
            install_piper(self.settings, progress=progress)
        return self.status()
