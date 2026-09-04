from __future__ import annotations

from core.models import ResearchItem


def compare_items(items: list[ResearchItem]) -> dict:
    priced = [item for item in items if item.price is not None]
    lowest = min(priced, key=lambda i: i.price) if priced else None
    return {
        "items": [
            {"title": i.title, "url": i.url, "price": i.price, "summary": i.relevant_text or i.snippet, "source": i.source}
            for i in items
        ],
        "lowest_price_title": lowest.title if lowest else None,
        "note": "Preços são os valores identificados nas fontes e podem mudar.",
    }
