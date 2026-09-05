from __future__ import annotations

from core.models import ResearchItem


def compare_items(items: list[ResearchItem]) -> dict:
    priced = [item for item in items if item.price is not None]
    lowest = min(priced, key=lambda i: i.price) if priced else None
    findings = [
        {"title": item.title, "fact": (item.relevant_text or item.snippet).strip()[:500], "source": item.url}
        for item in items if (item.relevant_text or item.snippet).strip()
    ]
    conclusion = (
        f"O menor preço identificado nas fontes foi {lowest.title}, por R$ {lowest.price:.2f}."
        if lowest else
        "As fontes não trouxeram preços comparáveis suficientes; a conclusão deve considerar os achados e links apresentados."
    )
    return {
        "items": [
            {"title": i.title, "url": i.url, "price": i.price, "summary": i.relevant_text or i.snippet, "source": i.source}
            for i in items
        ],
        "lowest_price_title": lowest.title if lowest else None,
        "summary": f"Foram comparadas {len(items)} fonte(s), sem preencher lacunas com fatos não encontrados.",
        "differences": findings,
        "pros_cons": {
            "pros": [],
            "cons": [],
            "note": "Prós e contras só são preenchidos quando aparecem explicitamente nas fontes.",
        },
        "conclusion": conclusion,
        "note": "Preços são os valores identificados nas fontes e podem mudar.",
    }
