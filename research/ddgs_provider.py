from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse
from core.models import ResearchItem
from research.search_provider import SearchProvider


class DDGSProvider(SearchProvider):
    def __init__(self) -> None:
        self._class = None
        try:
            from ddgs import DDGS
            self._class = DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
                self._class = DDGS
            except ImportError:
                pass

    def available(self) -> bool: return self._class is not None

    def search(self, query: str, max_results: int = 5) -> list[ResearchItem]:
        if not self._class: raise RuntimeError("O pacote 'ddgs' não está instalado.")
        results = self._class().text(query, region="br-pt", safesearch="moderate", max_results=max_results)
        items = []
        observed_at = datetime.now().astimezone().isoformat(timespec="seconds")
        for row in results or []:
            url = row.get("href") or row.get("url") or ""
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                continue
            items.append(ResearchItem(
                title=row.get("title") or url,
                url=url,
                snippet=row.get("body") or row.get("snippet") or "",
                source=urlparse(url).netloc,
                observed_at=observed_at,
            ))
        return items
