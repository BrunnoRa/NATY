import json
import os
import sys
import types
import unittest
from unittest.mock import patch

from connectors.base import ConfirmationRequired
from connectors.google.auth import GoogleAuth
from connectors.google.calendar import GoogleCalendarConnector
from connectors.google.credential_store import DpapiCredentialStore
from connectors.google.gmail import GmailConnector
from connectors.registry import ConnectorRegistry
from tests.base import TempDatabaseTest


class _Call:
    def __init__(self, value=None): self.value = value
    def execute(self): return self.value


class _GmailService:
    def __init__(self): self.sent = False; self.trashed = False; self.created = None
    def users(self): return self
    def messages(self): return self
    def drafts(self): return self
    def list(self, **_): return _Call({"messages": [{"id": "m1"}]})
    def get(self, **_): return _Call({"id": "m1", "threadId": "t1", "snippet": "Resumo", "payload": {"headers": [{"name": "Subject", "value": "Assunto"}, {"name": "From", "value": "Ana"}]}})
    def create(self, **kwargs): self.created = kwargs["body"]; return _Call({"id": "d1"})
    def send(self, **_): self.sent = True; return _Call({"id": "m2"})
    def trash(self, **_): self.trashed = True; return _Call({})


class _CalendarService:
    def __init__(self): self.deleted = False; self.body = None
    def events(self): return self
    def list(self, **_): return _Call({"items": [{"id": "e1", "summary": "Reunião"}]})
    def insert(self, **kwargs): self.body = kwargs["body"]; return _Call({"id": "e2", **self.body})
    def delete(self, **_): self.deleted = True; return _Call({})


class _Store:
    def __init__(self, value=None): self.value = value
    def load(self): return self.value
    def save(self, value): self.value = value
    def clear(self): self.value = None; return True


class ConnectorV2Tests(TempDatabaseTest):
    def test_registry_is_lazy(self):
        calls = []
        registry = ConnectorRegistry()
        registry.register("x", lambda: calls.append(1) or GmailConnector(service=_GmailService()))
        self.assertEqual(calls, [])
        self.assertFalse(registry.status()[0]["loaded"])
        registry.get("x")
        self.assertEqual(calls, [1])

    def test_gmail_read_draft_and_confirmation(self):
        service = _GmailService(); gmail = GmailConnector(service=service)
        messages = gmail.search("is:unread")
        self.assertEqual(messages[0]["subject"], "Assunto")
        self.assertEqual(gmail.create_draft("a@example.com", "Oi", "Corpo")["id"], "d1")
        with self.assertRaises(ConfirmationRequired): gmail.send_draft("d1")
        gmail.send_draft("d1", confirmed=True)
        self.assertTrue(service.sent)
        with self.assertRaises(ConfirmationRequired): gmail.delete("m1")

    def test_calendar_mock_and_delete_confirmation(self):
        service = _CalendarService(); calendar = GoogleCalendarConnector(service=service)
        self.assertEqual(calendar.upcoming()[0]["summary"], "Reunião")
        event = calendar.create("Teste", "2026-09-04T10:00:00-03:00")
        self.assertEqual(event["id"], "e2")
        with self.assertRaises(ConfirmationRequired): calendar.delete("e1")
        calendar.delete("e1", confirmed=True)
        self.assertTrue(service.deleted)

    def test_google_auth_reads_encrypted_store_contract(self):
        class FakeCredentials:
            valid, expired, refresh_token = True, False, "refresh"
            @classmethod
            def from_authorized_user_info(cls, info, scopes):
                self = cls(); self.info, self.scopes = info, scopes; return self

        modules = {
            "google": types.ModuleType("google"),
            "google.auth": types.ModuleType("google.auth"),
            "google.auth.transport": types.ModuleType("google.auth.transport"),
            "google.auth.transport.requests": types.SimpleNamespace(Request=lambda: object()),
            "google.oauth2": types.ModuleType("google.oauth2"),
            "google.oauth2.credentials": types.SimpleNamespace(Credentials=FakeCredentials),
        }
        auth = GoogleAuth("ignored.json", _Store(json.dumps({"token": "secret"})), scopes=("scope",))
        with patch.object(auth, "available", return_value=True), patch.dict(sys.modules, modules):
            self.assertTrue(auth.credentials().valid)

    @unittest.skipUnless(os.name == "nt", "DPAPI é específico do Windows")
    def test_dpapi_roundtrip_is_not_plaintext(self):
        path = self.root / "google.token"
        store = DpapiCredentialStore(path)
        try:
            store.save("segredo-oauth")
        except RuntimeError as exc:
            self.skipTest(f"perfil Windows indisponível no runner: {exc}")
        self.assertNotIn(b"segredo-oauth", path.read_bytes())
        self.assertEqual(store.load(), "segredo-oauth")
