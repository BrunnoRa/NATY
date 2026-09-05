from __future__ import annotations

import json
import unittest

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
