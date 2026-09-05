import unittest

from core.context import SessionContext
from nlu import intents
from nlu.parser import RuleParser
from tools.active_context import ActiveContextTool


class ActiveContextTests(unittest.TestCase):
    def test_context_keeps_minimal_bounded_session_history(self):
        context = SessionContext()
        for index in range(12):
            context.update_active_app({"process_name": "code", "window_title": f"Project {index}",
                                       "window_handle": index + 1, "timestamp": "2026-09-05T10:00:00-03:00",
                                       "typed_text": "must not be retained"})
        self.assertEqual(8, len(context.active_apps))
        self.assertNotIn("typed_text", context.active_app)

    def test_context_deduplicates_and_updates_timestamp(self):
        context = SessionContext()
        self.assertTrue(context.update_active_app({"process_name": "code", "window_title": "NATY", "window_handle": 12}))
        self.assertFalse(context.update_active_app({"process_name": "code", "window_title": "NATY", "window_handle": 12,
                                                    "timestamp": "later"}))
        self.assertEqual(1, len(context.active_apps))
        self.assertEqual("later", context.active_app["timestamp"])

    def test_active_context_answers_and_requests_existing_window_activation(self):
        context = SessionContext()
        context.update_active_app({"process_name": "Code", "window_title": "NATY - Visual Studio Code", "window_handle": 44})
        tool = ActiveContextTool(context)
        self.assertIn("Visual Studio Code", tool.show().message)
        result = tool.return_to_previous()
        self.assertTrue(result.ok)
        self.assertEqual({"active_app": context.active_app, "action": "activate_window", "window_handle": 44}, result.data)

    def test_active_context_does_not_invent_project_or_window(self):
        self.assertFalse(ActiveContextTool(SessionContext()).return_to_previous().ok)
        context = SessionContext()
        context.update_active_app({"process_name": "spotify", "window_title": "Spotify", "window_handle": 8})
        self.assertFalse(ActiveContextTool(context).return_to_previous(project_only=True).ok)

    def test_parser_routes_active_context_commands(self):
        parser = RuleParser()
        self.assertEqual(intents.ACTIVE_CONTEXT_STATUS, parser.parse("Naty, em que programa eu estou?").name)
        self.assertEqual(intents.ACTIVE_CONTEXT_RETURN, parser.parse("Volta para o que eu estava fazendo").name)
        self.assertEqual(intents.ACTIVE_CONTEXT_PROJECT, parser.parse("Abre o projeto que eu estava usando").name)
