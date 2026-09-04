from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ContextNote:
    title: str
    path: str
    excerpt: str
    score: float = 0.0


@dataclass(slots=True)
class ContextPack:
    query: str
    notes: list[ContextNote] = field(default_factory=list)
    structured: dict = field(default_factory=dict)
    max_chars: int = 8000

    def as_prompt_data(self) -> str:
        chunks, used = [], 0
        for note in self.notes:
            header = f"[DADO LOCAL: {note.title} | {note.path}]\n"
            footer = "\n[FIM DO DADO]"
            separator = "\n\n" if chunks else ""
            available = self.max_chars - used - len(separator) - len(header) - len(footer)
            excerpt = note.excerpt[:max(0, available)]
            if not excerpt: break
            chunk = header + excerpt + footer
            chunks.append(chunk); used += len(separator) + len(chunk)
        return "\n\n".join(chunks)
