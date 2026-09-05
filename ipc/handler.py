from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import os

from core.models import AppState
from ipc.protocol import ProtocolError, response


class CoreRequestHandler:
    SETTINGS_FIELDS = {
        "start_with_windows", "close_to_tray", "hotkey", "language",
        "microphone_device", "microphone_name", "stt_provider", "whisper_model_path",
        "tts_provider", "piper_model_path", "voice", "voice_rate", "voice_volume",
        "conversation_followup_seconds", "google_enabled", "chatgpt_handoff_enabled",
        "obsidian_enabled", "obsidian_vault_path", "naty_obsidian_path",
        "sync_enabled", "sync_folder", "device_name", "learning_mode",
        "proactivity_level", "privacy_mode",
        "daily_briefing_enabled", "daily_briefing_time",
        "quiet_hours_enabled", "quiet_hours_start", "quiet_hours_end",
        "safe_file_roots",
    }
    SETTINGS_ENUMS = {
        "learning_mode": {"manual", "assisted", "automatic_safe"},
        "proactivity_level": {"off", "important", "assistant"},
        "language": {"pt-BR"},
        "stt_provider": {"whisper_cpp", "vosk"},
        "tts_provider": {"piper", "sapi"},
    }

    def __init__(self, assistant):
        self.assistant = assistant
        self.shutdown_requested = False
        self._voice = None

    def _metrics(self) -> dict:
        try:
            import psutil
            root = psutil.Process(os.getpid())
            processes = [root, *root.children(recursive=True)]
            rss = sum(process.memory_info().rss for process in processes if process.is_running())
            cpu = sum(process.cpu_percent(interval=None) for process in processes if process.is_running())
            return {"ram_mib": round(rss / 1024 / 1024, 2), "cpu_percent": round(cpu, 2), "processes": len(processes)}
        except Exception:
            return {"ram_mib": None, "cpu_percent": None, "processes": 1}

    def _providers(self) -> list[dict]:
        settings = self.assistant.settings
        sync = self.assistant.sync.summary() if getattr(self.assistant, "sync", None) else {"status": "offline"}
        sync_status = sync["status"]
        sync_state = {"updated": "online", "syncing": "attention", "conflict": "error", "offline": "off"}.get(sync_status, "off")
        sync_label = {"updated": "✓ Atualizado", "syncing": "↻ Sincronizando", "conflict": "! Conflito", "offline": "○ Offline"}.get(sync_status, "○ Offline")
        return [
            {"name": "Voice", "state": "online" if settings.voice_enabled and self._voice_available() else "attention" if settings.voice_enabled else "off"},
            {"name": "Web", "state": "online" if settings.research_enabled else "off"},
            {"name": "Gmail", "state": "online" if hasattr(self.assistant, "google") and self.assistant.google.auth.status()["state"] == "connected" else
                                      self.assistant.google.auth.status()["state"] if hasattr(self.assistant, "google") else "off"},
            {"name": "Obsidian", "state": "online" if self.assistant.obsidian.available else "off"},
            {"name": "Spotify", "state": "off"},
            {"name": "Sync", "state": sync_state, "label": sync_label},
            {"name": "AI", "state": "online" if settings.ai_enabled and self.assistant.ai.available() else "off"},
        ]

    def _voice_available(self) -> bool:
        try:
            from voice.whisper_cpp import WhisperCppSTT
            from voice.vosk_stt import VoskSTT
            from voice.devices import resolve_microphone
            settings = self.assistant.settings
            microphone = resolve_microphone(settings.microphone_device,
                                            getattr(settings, "microphone_name", ""),
                                            getattr(settings, "microphone_hostapi", ""),
                                            getattr(settings, "microphone_sample_rate", 0))
            device = microphone["id"] if microphone else settings.microphone_device
            whisper = WhisperCppSTT(getattr(settings, "whisper_executable_path", ""),
                                    getattr(settings, "whisper_model_path", ""), device=device)
            return whisper.available() or VoskSTT(settings.vosk_model_path, device=device).available()
        except Exception:
            return False

    def _voice_controller(self):
        if self._voice is None:
            from voice.controller import VoiceController
            self._voice = VoiceController(self.assistant.settings, self._execute_text)
        return self._voice

    def _settings_payload(self) -> dict:
        settings = self.assistant.settings
        values = {name: getattr(settings, name) for name in self.SETTINGS_FIELDS}
        providers = {item["name"]: item["state"] for item in self._providers()}
        values["runtime"] = {
            "google": providers.get("Gmail", "off"),
            "obsidian": providers.get("Obsidian", "off"),
            "voice": providers.get("Voice", "off"),
            "spotify": "launcher/media",
            "sync": self.assistant.sync.summary() if getattr(self.assistant, "sync", None) else {
                "status": "offline", "last_sync": None, "pending": 0, "conflicts": 0, "device_id": "",
            },
            "memory_folder": str(settings.resolve_path(settings.data_dir)),
            "evolution_path": str(settings.managed_obsidian_path / "Evolução da NATY.md") if settings.managed_obsidian_path else "",
        }
        return values

    def _save_settings(self, incoming: dict) -> dict:
        settings = self.assistant.settings
        unknown = set(incoming) - self.SETTINGS_FIELDS
        if unknown:
            raise ProtocolError("Configuração não permitida.")
        for name, value in incoming.items():
            current = getattr(settings, name)
            if isinstance(current, bool):
                if not isinstance(value, bool):
                    raise ProtocolError(f"Valor inválido para {name}.")
            elif isinstance(current, int) and (not isinstance(value, int) or isinstance(value, bool)):
                raise ProtocolError(f"Valor inválido para {name}.")
            elif isinstance(current, str) and not isinstance(value, str):
                raise ProtocolError(f"Valor inválido para {name}.")
            if name in self.SETTINGS_ENUMS and value not in self.SETTINGS_ENUMS[name]:
                raise ProtocolError(f"Valor inválido para {name}.")
            setattr(settings, name, value)
        settings.save()
        return self._settings_payload()

    def _graph(self, active_terms=()) -> dict:
        nodes, edges = self.assistant.knowledge_graph.snapshot(limit=24)
        terms = {str(term).casefold() for term in active_terms if str(term).strip()}
        for node in nodes:
            node.active = any(term in node.title.casefold() or node.title.casefold() in term for term in terms)
        return {"nodes": [asdict(node) for node in nodes], "edges": [asdict(edge) for edge in edges]}

    @staticmethod
    def _active_terms(data) -> list[str]:
        if not isinstance(data, dict):
            return []
        terms = []
        for key in ("title", "name", "query", "text"):
            if data.get(key):
                terms.append(str(data[key]))
        for collection in ("notes", "tasks", "items"):
            for item in data.get(collection, []) if isinstance(data.get(collection), list) else []:
                if isinstance(item, dict):
                    terms.extend(str(item[key]) for key in ("title", "name", "text") if item.get(key))
        terms.extend(str(term) for term in data.get("_graph_terms", ()) if str(term).strip())
        return terms

    def _dashboard(self) -> dict:
        return {
            "tasks": self.assistant.task_repo.list()[:8],
            "projects": self.assistant.project_repo.list()[:6],
            "lists": self.assistant.list_repo.all()[:6],
            "providers": self._providers(),
            "metrics": self._metrics(),
            "graph": self._graph(),
            "state": self.assistant.state.value,
            "time": datetime.now().astimezone().isoformat(timespec="seconds"),
            "notifications": self.assistant.drain_notifications() if hasattr(self.assistant, "drain_notifications") else [],
            "sync": self.assistant.sync.summary() if getattr(self.assistant, "sync", None) else {"status": "offline", "pending": 0, "conflicts": 0},
            "ui_settings": {"close_to_tray": getattr(self.assistant.settings, "close_to_tray", True)},
            "suggestions": self.assistant.skills.suggestions(4) if hasattr(self.assistant, "skills") else [],
        }

    def _execute_text(self, text: str) -> dict:
        if not text or len(text) > 8000:
            raise ProtocolError("Texto vazio ou acima de 8.000 caracteres.")
        if hasattr(self.assistant, "handle_result"):
            result = self.assistant.handle_result(text)
            payload = result.payload()
            display_message = result.message.split("\n\nFontes:\n", 1)[0]
            payload["message"] = display_message
            payload["text"] = display_message
        else:
            answer = self.assistant.handle(text)
            payload = {"text": answer, "success": True, "type": "message", "data": None, "sources": [],
                       "ui": {"mode": "brain", "panel": "none", "title": ""}, "error": None}
        payload.update({"state": AppState.IDLE.value, "graph": self._graph(self._active_terms(payload.get("data")))})
        return payload

    def handle(self, message: dict) -> dict:
        type_ = message["type"]
        if type_ == "ping":
            return response(message, "pong", {"core": "NATY", "protocol": 1})
        if type_ == "status":
            return response(message, "status", {"state": self.assistant.state.value, "providers": self._providers(), "metrics": self._metrics()})
        if type_ == "dashboard":
            return response(message, "dashboard", self._dashboard())
        if type_ == "graph":
            return response(message, "graph", self._graph())
        if type_ == "user_input":
            if hasattr(self.assistant, "update_active_context"):
                self.assistant.update_active_context(message["payload"].get("active_app"))
            text = str(message["payload"].get("text", "")).strip()
            return response(message, "assistant_response", self._execute_text(text))
        if type_ == "voice_start":
            if hasattr(self.assistant, "update_active_context"):
                self.assistant.update_active_context(message["payload"].get("active_app"))
            return response(message, "voice_status", self._voice_controller().start())
        if type_ == "voice_status":
            return response(message, "voice_status", self._voice_controller().snapshot())
        if type_ == "voice_stop":
            return response(message, "voice_status", self._voice_controller().stop())
        if type_ == "voice_precision_start":
            expected = str(message["payload"].get("expected", ""))
            return response(message, "voice_precision_status", self._voice_controller().start_precision(expected))
        if type_ == "voice_precision_status":
            return response(message, "voice_precision_status", self._voice_controller().precision_snapshot())
        if type_ == "voice_precision_stop":
            return response(message, "voice_precision_status", self._voice_controller().stop_precision())
        if type_ == "settings_get":
            return response(message, "settings", self._settings_payload())
        if type_ == "settings_save":
            return response(message, "settings", self._save_settings(message["payload"]))
        if type_ == "sync_now":
            if not getattr(self.assistant, "sync", None):
                return response(message, "sync_status", {"status": "offline", "pending": 0, "conflicts": 0})
            try:
                return response(message, "sync_status", self.assistant.sync.sync_now())
            except (OSError, TimeoutError):
                self.assistant.sync.status = "offline"
                return response(message, "sync_status", self.assistant.sync.summary())
        if type_ == "diagnostics":
            hotkey = str(message["payload"].get("hotkey", "unknown"))
            return response(message, "diagnostics", self.assistant.diagnostics.run(hotkey, "ok", "ok"))
        if type_ == "workspace_list":
            return response(message, "workspace_list", {"workspaces": self.assistant.workspace_repo.list(False)})
        if type_ == "workspace_save":
            payload = message["payload"]
            result = self.assistant.workspaces.save(
                str(payload.get("name", "")), workspace_id=payload.get("workspace_id"),
                aliases=payload.get("aliases") if isinstance(payload.get("aliases"), list) else [],
                actions=payload.get("actions") if isinstance(payload.get("actions"), list) else [],
                focus_minutes=payload.get("focus_minutes"), enabled=bool(payload.get("enabled", True)),
            )
            return response(message, "workspace_result", result.payload())
        if type_ == "workspace_activate":
            result = self.assistant.workspaces.activate(str(message["payload"].get("name", "")))
            return response(message, "workspace_result", result.payload())
        if type_ == "shutdown":
            if self._voice is not None:
                self._voice.close()
            self.shutdown_requested = True
            return response(message, "shutdown_ack", {"clean": True})
        raise ProtocolError("Tipo não tratado.")
