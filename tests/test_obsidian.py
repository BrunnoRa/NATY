from pathlib import Path

from database.repositories.lists import ListRepository
from tests.base import TempDatabaseTest
from tools.obsidian import BEGIN, END, ObsidianTool, atomic_write


class ObsidianTests(TempDatabaseTest):
    def test_atomic_write(self):
        path = self.root / "file.md"; atomic_write(path, "olá")
        self.assertEqual(path.read_text(encoding="utf-8"), "olá")
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_sync_list_and_preserve_personal_content(self):
        repo = ListRepository(self.db); record = repo.create("Lista de Compras"); repo.add_item(record["id"], "Leite")
        vault = self.root / "vault"; vault.mkdir(); tool = ObsidianTool(True, str(vault), repo)
        path = tool.sync_list(record["id"]); self.assertIn("- [ ] Leite", path.read_text(encoding="utf-8"))
        path.write_text(path.read_text(encoding="utf-8") + "\nMinha nota pessoal\n", encoding="utf-8")
        repo.check(record["id"], "Leite"); tool.sync_list(record["id"])
        content = path.read_text(encoding="utf-8")
        self.assertIn("- [x] Leite", content); self.assertIn("Minha nota pessoal", content)
        self.assertEqual(content.count(BEGIN), 1); self.assertEqual(content.count(END), 1)

    def test_disabled_is_noop(self):
        repo = ListRepository(self.db); record = repo.create("X")
        self.assertIsNone(ObsidianTool(False, "", repo).sync_list(record["id"]))

    def test_rejects_managed_folder_outside_vault(self):
        repo = ListRepository(self.db); vault = self.root / "vault"; vault.mkdir()
        tool = ObsidianTool(True, str(vault), repo, str(self.root / "outside"))
        self.assertFalse(tool.available)
