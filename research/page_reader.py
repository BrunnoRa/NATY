from __future__ import annotations

from html.parser import HTMLParser
from urllib.request import Request, urlopen


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts: list[str] = []; self.ignored = 0
    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}: self.ignored += 1
    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self.ignored: self.ignored -= 1
    def handle_data(self, data):
        if not self.ignored and data.strip(): self.parts.append(data.strip())


class PageReader:
    def __init__(self, timeout: int = 10, max_size: int = 1_000_000): self.timeout, self.max_size = timeout, max_size

    def read(self, url: str) -> str:
        if not url.lower().startswith(("http://", "https://")): return ""
        request = Request(url, headers={"User-Agent": "Naty/1.0 (+local personal assistant)"})
        with urlopen(request, timeout=self.timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "text/plain" not in content_type: return ""
            raw = response.read(self.max_size + 1)
            if len(raw) > self.max_size: raw = raw[:self.max_size]
            charset = response.headers.get_content_charset() or "utf-8"
        parser = _TextExtractor(); parser.feed(raw.decode(charset, errors="replace"))
        return " ".join(parser.parts)[:20_000]
