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
        return [
            {"name": "Voice", "state": "online" if settings.voice_enabled and self._voice_available() else "attention" if settings.voice_enabled else "off"},
            {"name": "Web", "state": "online" if settings.research_enabled else "off"},
            {"name": "Gmail", "state": "online" if settings.google_enabled else "off"},
            {"name": "Obsidian", "state": "online" if self.assistant.obsidian.available else "off"},
            {"name": "Spotify", "state": "off"},
            {"name": "Sync", "state": "off"},
            {"name": "AI", "state": "online" if settings.ai_enabled and self.assistant.ai.available() else "off"},
        ]

    def _voice_available(self) -> bool:
        try:
            from voice.vosk_stt import VoskSTT
            settings = self.assistant.settings
            return VoskSTT(settings.vosk_model_path, device=settings.microphone_device).available()
        except Exception:
            return False

    def _graph(self) -> dict:
        nodes, edges = self.assistant.knowledge_graph.snapshot(limit=24)
        return {"nodes": [asdict(node) for node in nodes], "edges": [asdict(edge) for edge in edges]}

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
        }

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
            if not text or len(text) > 8000:
                raise ProtocolError("Texto vazio ou acima de 8.000 caracteres.")
            answer = self.assistant.handle(text)
            return response(message, "assistant_response", {"text": answer, "state": AppState.IDLE.value, "graph": self._graph()})
        if type_ == "shutdown":
            self.shutdown_requested = True
            return response(message, "shutdown_ack", {"clean": True})
        raise ProtocolError("Tipo não tratado.")
