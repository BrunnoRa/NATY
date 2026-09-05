"""Configuração leve e portátil da Naty."""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from pathlib import Path
import os
import sys
import tomllib


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_path(*parts: str) -> Path:
    """Resolve um recurso tanto no código-fonte quanto no bundle do PyInstaller."""
    bundle_root = Path(getattr(sys, "_MEIPASS", app_root()))
    return bundle_root.joinpath(*parts)


def user_data_root() -> Path:
    """Mantém dados mutáveis fora da instalação quando a Naty está empacotada."""
    if getattr(sys, "frozen", False) and os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "NATY"
    return app_root()


@dataclass(slots=True)
class Settings:
    first_run_completed: bool = False
    user_name: str = ""
    language: str = "pt-BR"
    hotkey: str = "CTRL+ALT+SPACE"
    voice_enabled: bool = True
    wake_word_enabled: bool = False
    tts_enabled: bool = True
    tts_provider: str = "sapi"
    piper_executable_path: str = ""
    piper_model_path: str = ""
    piper_config_path: str = ""
    piper_pause_ms: int = 120
    stt_provider: str = "whisper_cpp"
    vosk_model_path: str = ""
    whisper_executable_path: str = ""
    whisper_model_path: str = ""
    pre_roll_ms: int = 300
    end_silence_ms: int = 1100
    max_utterance_seconds: int = 20
    voice_model_idle_seconds: int = 30
    microphone_device: int = -1
    microphone_name: str = ""
    microphone_hostapi: str = ""
    microphone_sample_rate: int = 0
    microphone_gain: float = 12.0
    automatic_gain_enabled: bool = True
    voice: str = ""
    voice_rate: int = 0
    voice_volume: int = 100
    conversation_followup_seconds: int = 8
    unload_stt_after_use: bool = True
    ai_enabled: bool = False
    ai_model_path: str = ""
    ai_threads: int = 4
    ai_context_size: int = 2048
    ai_max_ram_mb: int = 1800
    ai_min_available_ram_mb: int = 2200
    ai_idle_unload_seconds: int = 120
    obsidian_enabled: bool = False
    obsidian_vault_path: str = ""
    naty_obsidian_path: str = ""
    obsidian_max_notes: int = 6
    obsidian_max_chars: int = 8000
    research_enabled: bool = True
    max_search_results: int = 5
    research_timeout_seconds: int = 10
    max_response_size: int = 1_000_000
    max_cpu_threads: int = 4
    start_with_windows: bool = False
    notifications_enabled: bool = True
    proactivity_enabled: bool = False
    morning_briefing: bool = False
    evening_review: bool = False
    overdue_followup: bool = True
    morning_briefing_time: str = "08:00"
    evening_review_time: str = "19:00"
    google_enabled: bool = False
    google_credentials_path: str = ""
    perplexity_enabled: bool = False
    performance_monitor_enabled: bool = True
    privacy_mode: bool = True
    learning_mode: str = "assisted"
    proactivity_level: str = "important"
    close_to_tray: bool = True
    chatgpt_handoff_enabled: bool = True
    sync_enabled: bool = False
    sync_folder: str = ""
    device_name: str = ""
    scheduler_interval_seconds: int = 30
    daily_summary_time: str = "08:00"
    data_dir: str = "data"
    log_dir: str = "logs"

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Settings":
        cfg_path = Path(path) if path else user_data_root() / "config.toml"
        settings = cls()
        if cfg_path.exists():
            raw = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
            raw = raw.get("naty", raw)
            allowed = {f.name for f in fields(cls)}
            for key, value in raw.items():
                if key in allowed:
                    setattr(settings, key, value)
        if not settings.vosk_model_path:
            bundled_model = resource_path("models", "vosk", "vosk-model-small-pt-0.3")
            if bundled_model.is_dir():
                settings.vosk_model_path = str(bundled_model)
        return settings

    def resolve_path(self, value: str) -> Path:
        path = Path(os.path.expandvars(value)).expanduser()
        return path if path.is_absolute() else user_data_root() / path

    @property
    def database_path(self) -> Path:
        return self.resolve_path(self.data_dir) / "naty.db"

    @property
    def logs_path(self) -> Path:
        return self.resolve_path(self.log_dir)

    @property
    def managed_obsidian_path(self) -> Path | None:
        """Pasta que a Naty pode gerenciar, sempre contida no Vault configurado."""
        if not self.obsidian_vault_path:
            return None
        vault = self.resolve_path(self.obsidian_vault_path).resolve()
        managed = self.resolve_path(self.naty_obsidian_path).resolve() if self.naty_obsidian_path else vault / "Naty"
        if managed != (vault / "Naty").resolve():
            return None
        return managed

    def as_dict(self) -> dict:
        return asdict(self)

    def save(self, path: str | Path | None = None) -> Path:
        cfg_path = Path(path) if path else user_data_root() / "config.toml"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["[naty]"]
        for key, value in self.as_dict().items():
            if isinstance(value, bool): encoded = "true" if value else "false"
            elif isinstance(value, str): encoded = '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
            else: encoded = str(value)
            lines.append(f"{key} = {encoded}")
        cfg_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return cfg_path
