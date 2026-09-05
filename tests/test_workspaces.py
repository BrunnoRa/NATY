from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from database.connection import Database
from database.migrations import migrate
from database.repositories.workspaces import WorkspaceRepository
from nlu import intents
from nlu.parser import RuleParser
from tools.windows_actions import WindowsActionsTool
from tools.workspaces import WorkspaceExecutor, WorkspaceTool


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        database = Database(Path(self.temporary.name) / "naty.db")
        migrate(database)
        self.opened = []
        windows = WindowsActionsTool(opener=self.opened.append)
        self.repository = WorkspaceRepository(database)
        self.tool = WorkspaceTool(self.repository, WorkspaceExecutor(windows))

    def tearDown(self): self.temporary.cleanup()

    def test_alias_activates_allowlisted_apps(self):
        saved = self.tool.save("Estudo", aliases=["foco"], actions=[{"type": "OPEN_APP", "value": "obsidian"}])
        self.assertTrue(saved.ok)
        result = self.tool.activate("foco")
        self.assertTrue(result.ok)
        self.assertEqual(["obsidian://open"], self.opened)
        self.assertTrue(self.repository.find("Estudo")["active"])

    def test_shell_and_unknown_apps_are_rejected_without_execution(self):
        shell = self.tool.save("Perigoso", actions=[{"type": "SHELL", "value": "powershell"}])
        unknown = self.tool.save("App", actions=[{"type": "OPEN_APP", "value": "unknown.exe"}])
        self.assertFalse(shell.ok)
        self.assertFalse(unknown.ok)
        self.assertEqual([], self.opened)

    def test_missing_file_is_reported_without_crashing_workspace(self):
        self.tool.save("Arquivo", actions=[{"type": "OPEN_FILE", "value": str(Path(self.temporary.name) / "missing.md")}])
        result = self.tool.activate("Arquivo")
        self.assertTrue(result.ok)
        self.assertEqual(1, len(result.data["errors"]))

    def test_workspace_commands_are_parsed(self):
        parser = RuleParser()
        self.assertEqual(intents.WORKSPACE_CREATE, parser.parse("Cria um modo chamado TCC").name)
        configured = parser.parse("Quando eu disser modo TCC, abre VS Code e Obsidian")
        self.assertEqual(["vscode", "obsidian"], configured.entities["apps"])
        self.assertEqual(intents.WORKSPACE_ACTIVATE, parser.parse("Naty, modo TCC").name)
        self.assertEqual(intents.WORKSPACE_LIST, parser.parse("Quais modos eu tenho?").name)


if __name__ == "__main__": unittest.main()
