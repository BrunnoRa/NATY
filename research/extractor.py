from __future__ import annotations

import re


def extract_price(text: str) -> float | None:
    matches = re.findall(r"R\$\s*([\d.]+(?:,\d{2})?)", text, re.I)
    values = []
    for raw in matches:
        try: values.append(float(raw.replace(".", "").replace(",", ".")))
        except ValueError: pass
    return min(values) if values else None


def relevant_excerpt(text: str, query: str, limit: int = 700) -> str:
    if not text: return ""
    terms = [term.lower() for term in re.findall(r"\w+", query) if len(term) > 3]
    lower = text.lower(); positions = [lower.find(term) for term in terms if lower.find(term) >= 0]
    start = max(0, (min(positions) if positions else 0) - 100)
    return text[start:start + limit].strip()
