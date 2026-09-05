from __future__ import annotations

import re
import unicodedata

from core.models import ToolResult


def _key(value: str) -> str:
    plain = "".join(c for c in unicodedata.normalize("NFD", value.casefold()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", plain).strip("-")[:120]


class SkillGapManager:
    def __init__(self, db, context, obsidian=None):
        self.db, self.context, self.obsidian = db, context, obsidian

    @property
    def pending(self) -> str | None:
        return self.context.state.get("pending_skill_gap")

    def propose(self, request_text: str) -> ToolResult:
        self.context.state["pending_skill_gap"] = request_text.strip()[:500]
        return ToolResult(False, "Não consegui identificar uma Skill configurada para esse pedido. Posso registrar isso como uma capacidade desejada?",
                          {"request": request_text.strip()[:500]}, type="skill_gap_proposal", error="unsupported_capability")

    def confirm(self) -> ToolResult:
        request_text = self.context.state.pop("pending_skill_gap", "")
        if not request_text: return ToolResult(False, "Não há capacidade aguardando confirmação.")
        normalized = _key(request_text)
        self.db.execute("""INSERT INTO skill_gaps(request_text,normalized_key) VALUES(?,?)
                           ON CONFLICT(normalized_key) DO UPDATE SET updated_at=CURRENT_TIMESTAMP""", (request_text, normalized))
        rows = self.list()
        path = self.obsidian.sync_skill_gaps(rows) if self.obsidian and self.obsidian.available else None
        detail = f" e atualizei {path}" if path else ""
        return ToolResult(True, f"Registrei essa capacidade desejada{detail}.", {"gap": request_text}, type="skill_gap_saved")

    def cancel(self) -> ToolResult:
        self.context.state.pop("pending_skill_gap", None)
        return ToolResult(True, "Tudo bem, não registrei essa sugestão.", type="skill_gap_cancelled")

    def list(self) -> list[dict]:
        return [dict(row) for row in self.db.query("SELECT * FROM skill_gaps ORDER BY updated_at DESC,id DESC")]
