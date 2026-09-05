from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from config import Settings
from ipc.handler import CoreRequestHandler
from ipc.protocol import ProtocolError, decode_message, encode_message, request


class FakeAI:
    def available(self): return False


class FakeSettings:
    voice_enabled = False
    research_enabled = True
    google_enabled = False
    ai_enabled = False
    vosk_model_path = ""
    microphone_device = -1
    microphone_name = ""
    stt_provider = "whisper_cpp"
    whisper_model_path = ""
    tts_provider = "sapi"
    piper_model_path = ""
    voice = ""
    voice_rate = 0
    voice_volume = 100
    conversation_followup_seconds = 8
    start_with_windows = False
    close_to_tray = True
    hotkey = "CTRL+ALT+SPACE"
    language = "pt-BR"
    chatgpt_handoff_enabled = True
    obsidian_enabled = False
    obsidian_vault_path = ""
    naty_obsidian_path = ""
    sync_enabled = False
    sync_folder = ""
    device_name = ""
    learning_mode = "assisted"
    proactivity_level = "important"
    privacy_mode = True
    data_dir = "data"
    managed_obsidian_path = None
    saved = False
    def resolve_path(self, value): return __import__("pathlib").Path(value)
    def save(self): self.saved = True


class FakeRepo:
    def __init__(self, rows=()): self.rows = list(rows)
    def list(self): return self.rows
    def all(self): return self.rows


class FakeGraph:
    def snapshot(self, limit=24): return [], []


class FakeObsidian:
    available = False


class FakeAssistant:
    settings = FakeSettings()
    state = type("State", (), {"value": "IDLE"})()
    ai = FakeAI()
    obsidian = FakeObsidian()
    knowledge_graph = FakeGraph()
    task_repo = FakeRepo([{"id": 1, "title": "Real"}])
    project_repo = FakeRepo()
    list_repo = FakeRepo()
    def handle(self, text): return f"Resposta: {text}"


class IPCProtocolTests(unittest.TestCase):
    def test_roundtrip_keeps_utf8_and_request_id(self):
        message = request("user_input", {"text": "adiciona café"}, "abc")
        self.assertEqual(decode_message(encode_message(message)), message)

    def test_rejects_wrong_protocol_and_unknown_type(self):
        with self.assertRaises(ProtocolError):
            decode_message(json.dumps({"protocol": 2, "type": "ping", "request_id": "1", "payload": {}}))
        with self.assertRaises(ProtocolError):
            decode_message(json.dumps({"protocol": 1, "type": "shell", "request_id": "1", "payload": {}}))

    def test_rejects_non_object_payload(self):
        with self.assertRaises(ProtocolError):
            decode_message(json.dumps({"protocol": 1, "type": "ping", "request_id": "1", "payload": []}))

    def test_user_input_returns_core_answer(self):
        response = CoreRequestHandler(FakeAssistant()).handle(request("user_input", {"text": "olá"}, "7"))
        self.assertEqual(response["type"], "assistant_response")
        self.assertEqual(response["request_id"], "7")
        self.assertEqual(response["payload"]["text"], "Resposta: olá")

    def test_dashboard_contains_real_repository_data(self):
        response = CoreRequestHandler(FakeAssistant()).handle(request("dashboard", request_id="8"))
        self.assertEqual(response["payload"]["tasks"][0]["title"], "Real")
        self.assertEqual(response["payload"]["providers"][1]["name"], "Web")

    def test_shutdown_is_explicit(self):
        handler = CoreRequestHandler(FakeAssistant())
        response = handler.handle(request("shutdown", request_id="9"))
        self.assertTrue(handler.shutdown_requested)
        self.assertEqual(response["type"], "shutdown_ack")

    def test_voice_messages_are_allowed_by_protocol(self):
        for type_ in ("voice_start", "voice_status", "voice_stop",
                      "voice_precision_start", "voice_precision_status", "voice_precision_stop"):
            message = request(type_, request_id=type_)
            self.assertEqual(decode_message(encode_message(message))["type"], type_)

    def test_settings_are_filtered_validated_and_persisted(self):
        handler = CoreRequestHandler(FakeAssistant())
        payload = handler.handle(request("settings_get", request_id="settings"))["payload"]
        self.assertIn("learning_mode", payload)
        self.assertNotIn("google_credentials_path", payload)

        updated = handler.handle(request("settings_save", {"learning_mode": "manual", "voice_volume": 75}))["payload"]
        self.assertEqual("manual", updated["learning_mode"])
        self.assertEqual(75, updated["voice_volume"])
        self.assertTrue(FakeAssistant.settings.saved)
        with self.assertRaises(ProtocolError):
            handler.handle(request("settings_save", {"google_credentials_path": "secret.json"}))

    def test_sync_messages_are_allowed_by_protocol(self):
        for type_ in ("settings_get", "settings_save", "sync_now", "diagnostics"):
            self.assertEqual(type_, decode_message(encode_message(request(type_)))["type"])

    def test_saved_settings_survive_reload(self):
        with tempfile.TemporaryDirectory() as directory, patch("config.user_data_root", return_value=Path(directory)):
            assistant = FakeAssistant()
            assistant.settings = Settings(voice_enabled=False, learning_mode="assisted")
            CoreRequestHandler(assistant).handle(request("settings_save", {
                "learning_mode": "automatic_safe", "close_to_tray": False,
            }))
            restored = Settings.load()
            self.assertEqual("automatic_safe", restored.learning_mode)
            self.assertFalse(restored.close_to_tray)
