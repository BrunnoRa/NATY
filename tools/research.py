from __future__ import annotations

import json
from datetime import date, datetime
from urllib.parse import urlparse

from core.models import ToolResult
from database.connection import Database
from research.comparison import compare_items
from research.browser_fallback import BrowserFallback
from research.ddgs_provider import DDGSProvider
from research.extractor import extract_price, relevant_excerpt
from research.page_reader import PageReader
from research.search_provider import SearchProvider
from research.session import ResearchSession
from tools.obsidian import ObsidianTool


class ResearchTool:
    def __init__(self, db: Database, provider: SearchProvider | None = None, max_results: int = 5,
                 timeout: int = 10, max_size: int = 1_000_000, obsidian: ObsidianTool | None = None, enabled: bool = True):
        self.db, self.provider = db, provider or DDGSProvider()
        self.max_results, self.reader, self.obsidian = max_results, PageReader(timeout, max_size), obsidian
        self.last_query, self.enabled = "", enabled
        self.browser_fallback = BrowserFallback()

    def search(self, query: str, compare: bool = False, read_pages: bool = False) -> ToolResult:
        if not query.strip(): return ToolResult(False, "O que você quer pesquisar?")
        if not self.enabled: return ToolResult(False, "A pesquisa web está desativada nas configurações.")
        self.last_query = query.strip()
        if not self.provider.available():
            return ToolResult(False, "A pesquisa web não está disponível. Instale o extra de pesquisa; suas tarefas continuam funcionando.", {"browser_query": query})
        try:
            items = self.provider.search(query, self.max_results)
            observed_now = datetime.now().astimezone().isoformat(timespec="seconds")
            if read_pages:
                for item in items[:3]:
                    if not item.observed_at: item.observed_at = observed_now
                    try:
                        page = self.reader.read(item.url)
                        item.relevant_text = relevant_excerpt(page, query)
                        item.price = None if self._looks_like_listing(item.url) else extract_price(item.relevant_text or item.snippet)
                    except Exception: continue
            else:
                for item in items:
                    if not item.observed_at: item.observed_at = observed_now
                    item.price = None if self._looks_like_listing(item.url) else extract_price(item.snippet)
            comparison = compare_items(items) if compare else {}
            session = ResearchSession.from_items(query, items, comparison)
            payload = session.payload()
            if compare:
                payload.update({key: value for key, value in comparison.items() if key != "items"})
            research_id = self.db.execute("INSERT INTO research_history(query, result_json) VALUES (?, ?)", (query, json.dumps(payload, ensure_ascii=False)))
            for claim in session.claims:
                self.db.execute(
                    "INSERT INTO research_claims(research_id, claim, source_url, confidence, observed_at) VALUES (?, ?, ?, ?, ?)",
                    (research_id, claim.text, claim.source_url, claim.confidence, claim.observed_at),
                )
            if not items: return ToolResult(True, "Não encontrei resultados para essa pesquisa.", payload)
            lines = [f"{idx}. {item.title}" + (f" — R$ {item.price:.2f} (observado em {item.observed_at})" if item.price is not None else "") for idx, item in enumerate(items, 1)]
            message = f"Encontrei {len(items)} resultado(s):\n" + "\n".join(lines)
            sources = [{"title": i.title, "url": i.url} for i in items]
            return ToolResult(True, message, payload, sources=sources)
        except Exception as exc:
            return ToolResult(False, f"A pesquisa falhou ({type(exc).__name__}). Posso abrir a busca no navegador; o restante da Naty continua disponível.", {"browser_query": query})

    @staticmethod
    def _looks_like_listing(url: str) -> bool:
        path = urlparse(url).path.casefold()
        return any(marker in path.split("/") for marker in ("busca", "search", "lista", "listagem")) or "lista.mercadolivre" in url.casefold()

    @staticmethod
    def open_browser(query: str) -> None:
        BrowserFallback().open(query)

    def open_last_in_browser(self) -> ToolResult:
        if not self.last_query: return ToolResult(False, "Faça uma pesquisa primeiro.")
        self.open_browser(self.last_query)
        return ToolResult(True, "Abri a pesquisa no navegador.")

    def save_last_to_obsidian(self) -> ToolResult:
        row = self.db.one("SELECT * FROM research_history ORDER BY id DESC LIMIT 1")
        if not row: return ToolResult(False, "Ainda não há pesquisa para salvar.")
        if not self.obsidian or not self.obsidian.available: return ToolResult(False, "Configure um Vault do Obsidian primeiro.")
        payload = json.loads(row["result_json"]); items = payload.get("items", [])
        sources = "\n".join(f"- [{i.get('title', 'Fonte')}]({i.get('url', '')}) — observado em {i.get('observed_at') or payload.get('created_at', '')}" for i in items)
        results = "\n\n".join(
            f"### {i.get('title', 'Resultado')}\n\n{i.get('relevant_text') or i.get('summary') or i.get('snippet') or ''}"
            for i in items
        )
        comparison = payload.get("comparison") or {}
        comparison_text = comparison.get("note", "Não solicitada.") if comparison else "Não solicitada."
        body = (
            f"Data: {payload.get('created_at') or date.today().isoformat()}\n\n"
            f"Consulta: {row['query']}\n\n"
            "## Resumo\n\nResultados preservados com suas fontes e data de observação.\n\n"
            f"## Resultados\n\n{results or 'Nenhum resultado.'}\n\n"
            f"## Comparação\n\n{comparison_text}\n\n"
            f"## Fontes\n\n{sources or 'Nenhuma fonte.'}\n\n"
            "## Minha decisão\n\n- [ ] Registrar decisão\n\n"
            "Relacionados: [[Painel Principal]] · [[Projetos Ativos]]"
        )
        path = self.obsidian.save_note("Pesquisas", f"Pesquisa - {row['query']}", body)
        self.db.execute("UPDATE research_history SET saved_to_obsidian = 1 WHERE id = ?", (row["id"],))
        return ToolResult(True, f"Salvei a pesquisa no Obsidian: {path}.", {"path": str(path)})
