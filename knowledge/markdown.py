from __future__ import annotations

import re


WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")


def parse_markdown(text: str) -> dict:
    frontmatter, body = {}, text
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end >= 0:
            raw, body = text[4:end], text[end + 4:].lstrip("\r\n")
            for line in raw.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1); frontmatter[key.strip()] = value.strip().strip('"\'')
    title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else ""
    tags = sorted(set(re.findall(r"(?<!\w)#([\w\-/à-ÿ]+)", body, re.I)))
    wikilinks = sorted(set(m.group(1).strip() for m in WIKILINK_RE.finditer(body)))
    plain = re.sub(r"```.*?```", " ", body, flags=re.DOTALL)
    plain = re.sub(r"[`*_>#\[\]()-]", " ", plain)
    plain = re.sub(r"\s+", " ", plain).strip()
    return {"title": title, "frontmatter": frontmatter, "tags": tags, "wikilinks": wikilinks, "body": body, "plain": plain}


def yaml_frontmatter(type_: str, created: str, updated: str | None = None, status: str | None = None) -> str:
    lines = ["---", "naty_managed: true", f"type: {type_}", f"created: {created}", f"updated: {updated or created}"]
    if status: lines.append(f"status: {status}")
    return "\n".join(lines + ["---", ""])
