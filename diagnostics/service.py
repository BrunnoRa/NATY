from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from voice.piper_setup import diagnostics as piper_diagnostics
from voice.whisper_setup import diagnostics as whisper_diagnostics


@dataclass(slots=True)
class DiagnosticItem:
    name: str
    state: str
    message: str
    technical: str = ""


class DiagnosticService:
    def __init__(self, assistant):
        self.assistant = assistant

    def run(self, hotkey_state: str = "unknown", desktop_state: str = "unknown", pipe_state: str = "unknown") -> dict:
        settings = self.assistant.settings
        items = [
            DiagnosticItem("Desktop", "ok" if desktop_state == "ok" else "warning",
                           "Desktop WPF respondeu à solicitação." if desktop_state == "ok" else "Estado do Desktop não informado ao Core."),
            DiagnosticItem("Core", "ok", "Core Python está em execução."),
            DiagnosticItem("Pipe", "ok" if pipe_state == "ok" else "warning",
                           "Named Pipe v1 está conectado." if pipe_state == "ok" else "Estado do pipe não confirmado por um cliente."),
            self._sqlite(),
            self._obsidian(),
        ]
        whisper = whisper_diagnostics(settings.whisper_executable_path, settings.whisper_model_path)
        items.append(DiagnosticItem("Whisper", "ok" if whisper["ready"] else "not_configured",
                                    whisper["status"], whisper.get("runtime_path", "")))
        piper = piper_diagnostics(settings.piper_executable_path, settings.piper_model_path, settings.piper_config_path)
        items.append(DiagnosticItem("Piper", "ok" if piper["ready"] else "not_configured",
                                    piper["status"], piper.get("executable_path", "")))
        items.extend((self._google(), self._sync(), self._hotkey(hotkey_state)))
        return {
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "overall": "error" if any(item.state == "error" for item in items) else
                       "warning" if any(item.state in {"warning", "not_configured"} for item in items) else "ok",
            "items": [asdict(item) for item in items],
            "summary": self.summary(items),
        }

    def _sqlite(self) -> DiagnosticItem:
        try:
            self.assistant.db.one("SELECT 1")
            return DiagnosticItem("SQLite", "ok", "Banco local e memória persistente estão funcionando.", str(self.assistant.db.path))
        except Exception as exc:
            return DiagnosticItem("SQLite", "error", "Não foi possível consultar o banco local.", type(exc).__name__)

    def _obsidian(self) -> DiagnosticItem:
        if not self.assistant.settings.obsidian_enabled:
            return DiagnosticItem("Obsidian", "not_configured", "Obsidian não está habilitado.")
        if self.assistant.obsidian.available:
            return DiagnosticItem("Obsidian", "ok", "Vault gerenciado está disponível.", str(self.assistant.obsidian.base))
        return DiagnosticItem("Obsidian", "warning", "O caminho configurado do Obsidian não está disponível.")

    def _google(self) -> DiagnosticItem:
        state = self.assistant.google.auth.status().get("state", "not_configured") if hasattr(self.assistant, "google") else "not_configured"
        if state in {"connected", "online"}:
            return DiagnosticItem("Google", "ok", "Conta Google conectada.")
        if state == "error":
            return DiagnosticItem("Google", "error", "A integração Google precisa de atenção.")
        return DiagnosticItem("Google", "not_configured", "Google ainda não foi configurado.")

    def _sync(self) -> DiagnosticItem:
        sync = getattr(self.assistant, "sync", None)
        if not sync:
            return DiagnosticItem("Sync", "not_configured", "Sincronização está desabilitada.")
        summary = sync.summary()
        state = summary.get("status", "offline")
        mapped = {"updated": "ok", "syncing": "warning", "conflict": "warning", "offline": "warning"}.get(state, "warning")
        message = {"updated": "Sincronização está atualizada.", "syncing": "Sincronização em andamento.",
                   "conflict": "Há conflitos de sincronização para revisar.", "offline": "Pasta de sincronização está offline."}.get(state, state)
        return DiagnosticItem("Sync", mapped, message, str(summary.get("folder", "")))

    @staticmethod
    def _hotkey(state: str) -> DiagnosticItem:
        if state == "registered":
            return DiagnosticItem("Hotkey", "ok", "Hotkey global registrada.")
        if state == "conflict":
            return DiagnosticItem("Hotkey", "warning", "A hotkey está em uso por outro aplicativo.")
        return DiagnosticItem("Hotkey", "warning", "O Core não recebeu o estado da hotkey do Desktop.")

    @staticmethod
    def summary(items: list[DiagnosticItem]) -> str:
        by_name = {item.name: item for item in items}
        parts = ["Core e memória estão funcionando." if by_name["SQLite"].state == "ok" else "A memória local precisa de atenção."]
        parts.append("Whisper está instalado." if by_name["Whisper"].state == "ok" else "Whisper ainda não está configurado.")
        parts.append("Google está conectado." if by_name["Google"].state == "ok" else "Google ainda não foi conectado.")
        parts.append(by_name["Sync"].message)
        return " ".join(parts)
