from __future__ import annotations

from urllib.parse import quote_plus
import webbrowser


class BrowserFallback:
    """Builds a transparent fallback URL and opens it only on explicit action."""

    @staticmethod
    def url(query: str) -> str:
        return f"https://duckduckgo.com/?q={quote_plus(query.strip())}"

    def open(self, query: str) -> bool:
        return bool(webbrowser.open(self.url(query)))
