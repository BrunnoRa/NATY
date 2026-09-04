from pathlib import Path

from activation.hotkey import MODIFIERS, parse_hotkey
from ai.no_ai import NoAIProvider
from core.assistant import NatyAssistant
from core.context import SessionContext
from tests.base import TempDatabaseTest


class CoreTests(TempDatabaseTest):
    def assistant(self): return NatyAssistant(self.settings(), self.db)

    def test_short_context(self):
        context = SessionContext(max_turns=2)
        for n in range(3): context.remember_turn(str(n), str(n))
        self.assertEqual(len(context.turns), 2)

    def test_contextual_task_update(self):
        app = self.assistant(); app.handle("cria tarefa revisar texto amanhã"); response = app.handle("coloca como prioridade alta")
        self.assertIn("Atualizei", response); self.assertEqual(self.db.one("SELECT priority FROM tasks")["priority"], "high")

    def test_contextual_list(self):
        app = self.assistant(); app.handle("cria uma lista chamada viagem"); app.handle("adiciona escova")
        self.assertEqual(self.db.one("SELECT text FROM list_items")["text"], "escova")

    def test_delete_needs_confirmation(self):
        app = self.assistant(); app.handle("cria tarefa teste")
        self.assertIn("confirmar", app.handle("apaga todas as tarefas")); self.assertEqual(self.db.one("SELECT COUNT(*) c FROM tasks")["c"], 1)
        app.handle("sim"); self.assertEqual(self.db.one("SELECT COUNT(*) c FROM tasks")["c"], 0)

    def test_ai_disabled(self): self.assertFalse(NoAIProvider().is_available())
    def test_voice_disabled_setting(self): self.assertFalse(self.settings().voice_enabled)

    def test_hotkey_parser(self):
        modifiers, key = parse_hotkey("CTRL+ALT+SPACE")
        self.assertEqual(modifiers, MODIFIERS["CTRL"] | MODIFIERS["ALT"]); self.assertEqual(key, 0x20)

    def test_configuration_roundtrip(self):
        vault = self.root / "Vault"
        settings = self.settings(language="pt-BR", max_search_results=3, obsidian_vault_path=str(vault), naty_obsidian_path=str(vault / "Naty")); path = self.root / "config.toml"
        settings.save(path); loaded = type(settings).load(path)
        self.assertEqual(loaded.max_search_results, 3); self.assertEqual(loaded.language, "pt-BR")
        self.assertEqual(loaded.managed_obsidian_path, (vault / "Naty").resolve())

    def test_managed_obsidian_path_cannot_escape_vault(self):
        vault = self.root / "Vault"
        settings = self.settings(obsidian_vault_path=str(vault), naty_obsidian_path=str(self.root / "Outside"))
        self.assertIsNone(settings.managed_obsidian_path)
