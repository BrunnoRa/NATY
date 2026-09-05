from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import os

from core.models import AppState
from ipc.protocol import ProtocolError, response


class CoreRequestHandler:
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
            {"name": "Gmail", "state": self.assistant.google.auth.status()["state"] if hasattr(self.assistant, "google") else "off"},
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
            text = str(message["payload"].get("text", "")).strip()
            return response(message, "assistant_response", self._execute_text(text))
        if type_ == "voice_start":
            return response(message, "voice_status", self._voice_controller().start())
        if type_ == "voice_status":
            return response(message, "voice_status", self._voice_controller().snapshot())
        if type_ == "voice_stop":
            return response(message, "voice_status", self._voice_controller().stop())
        if type_ == "shutdown":
            if self._voice is not None:
                self._voice.close()
            self.shutdown_requested = True
            return response(message, "shutdown_ack", {"clean": True})
        raise ProtocolError("Tipo não tratado.")
