from __future__ import annotations

from core.assistant import NatyAssistant
from diagnostics.service import DiagnosticService
from tests.base import TempDatabaseTest


class DiagnosticsTests(TempDatabaseTest):
    def setUp(self):
        super().setUp()
        self.assistant = NatyAssistant(self.settings(obsidian_enabled=False, google_enabled=False), self.db)

    def tearDown(self):
        self.assistant.close()
        super().tearDown()

    def test_report_uses_real_component_state(self):
        report = DiagnosticService(self.assistant).run("registered")
        items = {item["name"]: item for item in report["items"]}
        self.assertEqual("ok", items["SQLite"]["state"])
        self.assertEqual("not_configured", items["Google"]["state"])
        self.assertEqual("not_configured", items["Sync"]["state"])
        self.assertEqual("ok", items["Hotkey"]["state"])
        self.assertNotIn("Traceback", str(report))

    def test_how_are_you_command_is_not_hardcoded_success(self):
        result = self.assistant.handle_result("Naty, como você está?")
        self.assertTrue(result.ok)
        self.assertEqual("diagnostics", result.type)
        self.assertIn("Google ainda não foi conectado", result.message)
        self.assertEqual("not_configured", next(item for item in result.data["items"] if item["name"] == "Google")["state"])
