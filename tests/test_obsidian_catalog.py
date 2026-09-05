from pathlib import Path

from knowledge.graph import KnowledgeGraph
from knowledge.obsidian_index import ObsidianIndex
from scripts.sync_obsidian_catalog import sync_catalog
from tests.base import TempDatabaseTest


class ObsidianCatalogTests(TempDatabaseTest):
    def test_catalog_is_generated_from_real_skills_and_is_idempotent(self):
        managed = self.root / "Vault" / "Naty"
        changed = sync_catalog(managed)
        self.assertTrue(changed)
        capabilities = (managed / "00 - Sistema" / "Capacidades.md").read_text(encoding="utf-8")
        self.assertIn("system_status", capabilities)
        self.assertIn("clipboard", capabilities)
        self.assertEqual([], sync_catalog(managed))

    def test_generated_skills_are_found_by_fts_and_graph(self):
        vault = self.root / "Vault"; managed = vault / "Naty"
        sync_catalog(managed)
        report = ObsidianIndex(self.db, vault, managed).index(validate=True)
        self.assertEqual(0, report["invalid_markdown"])
        results = ObsidianIndex(self.db, vault, managed).search("clipboard briefing workspace")
        self.assertTrue(any("Clipboard" in item["title"] for item in results))
        KnowledgeGraph(self.db).rebuild()
        nodes, _ = KnowledgeGraph(self.db).snapshot(100)
        self.assertTrue(any(node.type == "skill" for node in nodes))
