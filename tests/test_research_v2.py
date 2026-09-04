from core.models import ResearchItem
from research.session import ResearchSession
from research.search_provider import SearchProvider
from tests.base import TempDatabaseTest
from tools.research import ResearchTool
from tools.obsidian import ObsidianTool
from database.repositories.lists import ListRepository


class Provider(SearchProvider):
    def available(self): return True
    def search(self, query, max_results=5):
        return [ResearchItem("Fonte", "https://example.com/x", "Uma alegação verificável", observed_at="2026-09-04T10:00:00-03:00")]


class ResearchV2Tests(TempDatabaseTest):
    def test_session_keeps_claim_source_and_timestamp(self):
        session = ResearchSession.from_items("teste", Provider().search("teste"))
        claim = session.payload()["claims"][0]
        self.assertEqual(claim["source_url"], "https://example.com/x")
        self.assertTrue(claim["observed_at"])

    def test_tool_persists_claims(self):
        result = ResearchTool(self.db, Provider()).search("teste")
        self.assertTrue(result.ok)
        row = self.db.one("SELECT * FROM research_claims")
        self.assertEqual(row["source_url"], "https://example.com/x")

    def test_cross_check_requires_another_domain(self):
        items = [
            ResearchItem("A", "https://a.example/x", "cadeira modelo alfa suporta cento e vinte quilos"),
            ResearchItem("B", "https://b.example/y", "cadeira modelo alfa suporta cento e vinte quilos"),
        ]
        claims = ResearchSession.from_items("cadeira", items).claims
        self.assertEqual(claims[0].confidence, 0.75)
        self.assertEqual(claims[0].corroborated_by, ["https://b.example/y"])

    def test_saved_research_has_decision_and_sources(self):
        vault = self.root / "Vault"; vault.mkdir()
        obsidian = ObsidianTool(True, str(vault), ListRepository(self.db))
        tool = ResearchTool(self.db, Provider(), obsidian=obsidian)
        tool.search("teste")
        result = tool.save_last_to_obsidian()
        self.assertTrue(result.ok)
        content = result.data["path"]
        text = Path(content).read_text(encoding="utf-8")
        self.assertIn("## Fontes", text)
        self.assertIn("## Minha decisão", text)

    def test_listing_page_does_not_claim_product_price(self):
        class ListingProvider(SearchProvider):
            def available(self): return True
            def search(self, query, max_results=5): return [ResearchItem("Busca", "https://loja.example/busca/ssd", "12x de R$ 23,00")]
        result = ResearchTool(self.db, ListingProvider()).search("ssd")
        self.assertIsNone(result.data["items"][0]["price"])
from pathlib import Path
