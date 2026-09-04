from core.models import ResearchItem
from research.extractor import extract_price
from research.search_provider import SearchProvider
from tests.base import TempDatabaseTest
from tools.research import ResearchTool


class FakeProvider(SearchProvider):
    def available(self): return True
    def search(self, query, max_results=5):
        return [ResearchItem("Monitor A", "https://example.com/a", "Oferta por R$ 899,90", source="example.com")]


class OfflineProvider(SearchProvider):
    def available(self): return False
    def search(self, query, max_results=5): raise AssertionError("não deveria buscar")


class ResearchTests(TempDatabaseTest):
    def test_price_extraction(self): self.assertEqual(extract_price("de R$ 1.299,90 por R$ 899,00"), 899.0)

    def test_search_keeps_sources(self):
        result = ResearchTool(self.db, FakeProvider()).search("monitor")
        self.assertTrue(result.ok); self.assertEqual(result.sources[0]["url"], "https://example.com/a")
        self.assertEqual(self.db.one("SELECT COUNT(*) c FROM research_history")["c"], 1)

    def test_offline_fallback(self):
        result = ResearchTool(self.db, OfflineProvider()).search("monitor")
        self.assertFalse(result.ok); self.assertEqual(result.data["browser_query"], "monitor")

    def test_disabled(self):
        result = ResearchTool(self.db, FakeProvider(), enabled=False).search("monitor")
        self.assertFalse(result.ok); self.assertIn("desativada", result.message)
