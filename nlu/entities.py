from __future__ import annotations

import re


def split_items(text: str) -> list[str]:
    text = re.sub(r"\s*,\s*", "|", text.strip())
    text = re.sub(r"\s+e\s+", "|", text, flags=re.IGNORECASE)
    return [item.strip(" .") for item in text.split("|") if item.strip(" .")]


def normalize_list_name(name: str) -> str:
    clean = re.sub(r"^(?:a |da |de |do )", "", name.strip(), flags=re.I)
    aliases = {"compra": "Lista de Compras", "compras": "Lista de Compras", "lista de compra": "Lista de Compras", "lista de compras": "Lista de Compras"}
    return aliases.get(clean.lower(), clean.title())


def parse_minutes(text: str) -> int | None:
    match = re.search(r"\b(\d{1,4})\s*(?:minutos?|min)\b", text, re.I)
    return int(match.group(1)) if match else None
