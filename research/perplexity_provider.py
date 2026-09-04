from __future__ import annotations

import json
import os
from datetime import datetime
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from core.models import ResearchItem
from research.search_provider import SearchProvider


class PerplexityProvider(SearchProvider):
    """Optional paid provider. It is inert without explicit config and an env key."""

    ENDPOINT = "https://api.perplexity.ai/chat/completions"

    def __init__(self, enabled: bool = False, api_key: str | None = None, timeout: int = 20):
        self.enabled = enabled
        self.api_key = api_key or os.environ.get("NATY_PERPLEXITY_API_KEY", "")
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self.enabled and self.api_key)

    def search(self, query: str, max_results: int = 5) -> list[ResearchItem]:
        if not self.available():
            raise RuntimeError("Perplexity não está habilitado ou não possui chave no ambiente.")
        payload = {
            "model": "sonar",
            "messages": [{"role": "user", "content": f"Pesquise e resuma com fontes: {query}"}],
            "max_tokens": 700,
            "temperature": 0.1,
        }
        request = Request(
            self.ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            result = json.loads(response.read(1_000_000).decode("utf-8"))
        text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        citations = result.get("citations") or []
        observed = datetime.now().astimezone().isoformat(timespec="seconds")
        return [
            ResearchItem(
                title=f"Fonte {index + 1}", url=url, snippet=text if index == 0 else "",
                source=urlparse(url).netloc, observed_at=observed,
            )
            for index, url in enumerate(citations[:max_results]) if isinstance(url, str)
        ]
