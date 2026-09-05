from __future__ import annotations

import unittest

from nlu import intents
from nlu.parser import RuleParser
from tools.google_workspace import GoogleWorkspaceTool


class Settings:
    google_enabled = False
    def save(self): pass


class Auth:
    scopes = ()
    def available(self): return False
    def status(self): return {"state": "not_configured", "connected": False}


class NeverCalled:
    def __getattr__(self, name): raise AssertionError(f"API não deveria ser chamada: {name}")


class DB:
    def execute(self, *args): pass


class GoogleCycleTests(unittest.TestCase):
    def test_unconfigured_google_is_friendly_and_does_not_call_api(self):
        tool = GoogleWorkspaceTool(Settings(), DB(), Auth(), NeverCalled(), NeverCalled())
        for result in (tool.search_mail("is:unread"), tool.draft("a@b.com", "Oi", "Olá"), tool.upcoming(), tool.is_free("2026-09-05T15:00:00")):
            self.assertFalse(result.ok)
            self.assertEqual(result.error, "not_configured")
            self.assertIn("Google ainda não conectado", result.message)

    def test_availability_phrase_routes_to_google(self):
        parsed = RuleParser().parse("Estou livre sexta às 15h?")
        self.assertEqual(parsed.name, intents.GOOGLE_CALENDAR_FREE)
        self.assertIsNotNone(parsed.entities["starts_at"])


if __name__ == "__main__": unittest.main()
