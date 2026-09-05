import unittest

from core.assistant import NatyAssistant
from skills.registry import build_registry
from tests.base import TempDatabaseTest


class DummyRouter:
    def execute(self, intent): return None


class SkillCatalogTests(TempDatabaseTest):
    def test_every_skill_exposes_complete_metadata(self):
        registry = build_registry(DummyRouter())
        for skill in registry.status():
            self.assertTrue(skill["description"])
            self.assertTrue(skill["category"])
            self.assertIsInstance(skill["requires_network"], bool)
            self.assertIsInstance(skill["requires_confirmation"], bool)
            self.assertIsInstance(skill["requires_credentials"], bool)
            self.assertTrue(skill["ui_panel"])
            self.assertTrue(skill["examples"])

    def test_suggestions_come_from_registered_skills(self):
        registry = build_registry(DummyRouter())
        examples = {example for skill in registry.status() for example in skill["examples"]}
        suggestions = registry.suggestions()
        self.assertLessEqual(len(suggestions), 4)
        self.assertTrue(set(suggestions).issubset(examples))

    def test_self_knowledge_uses_registry_and_runtime_status(self):
        assistant = NatyAssistant(self.settings(), self.db)
        result = assistant.handle_result("Naty, o que você sabe fazer?")
        self.assertTrue(result.ok)
        self.assertEqual(len(assistant.skills.status()), len(result.data["skills"]))
        self.assertIn("Skills ativas", result.message)
        version = assistant.handle_result("Qual versão você está?")
        self.assertEqual("3.1.0", version.data["version"])
