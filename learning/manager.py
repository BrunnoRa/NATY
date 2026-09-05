from __future__ import annotations

from datetime import datetime
import json
import re

from core.models import ToolResult


class LearningManager:
    def __init__(self, memories, obsidian=None, mode: str = "assisted"):
        self.memories, self.obsidian, self.mode = memories, obsidian, mode
        self.pending: dict | None = None

    def detect(self, text: str) -> dict | None:
        if self.mode == "off": return None
        rules = (
            ("NEW_PREFERENCE", r"\b(?:eu\s+)?prefiro(?:\s+que\s+você)?\s+(.+)"),
            ("DECISION", r"\b(?:eu\s+)?decidi\s+(.+)"),
            ("CORRECTION", r"^(?:correção|na verdade|não,? você deve)\s*[:,-]?\s*(.+)"),
            ("NEW_ROUTINE", r"\b(?:todo dia|toda manhã|toda noite|sempre)\s+(.+)"),
            ("NEW_PROJECT_INFO", r"\b(?:meu|o) projeto\s+(.+)"),
        )
        for type_, pattern in rules:
            match = re.search(pattern, text.strip(), re.I)
            if match:
                return {"type": type_, "value": match.group(1).strip(" ."), "origin": text.strip()}
        return None

    def propose(self, candidate: dict) -> ToolResult:
        self.pending = candidate
        label = candidate["value"]
        return ToolResult(False, f"Percebi uma nova informação: {label}. Quer que eu guarde?",
                          candidate, type="learning_confirmation",
                          ui_hint={"mode": "context", "panel": "learning", "title": "Aprendizado assistido"})

    def queue_external(self, data: dict, origin: str = "resultado externo") -> None:
        self.pending = {"type": "EXTERNAL_IMPORT", "value": json.dumps(data, ensure_ascii=False), "origin": origin}

    def confirm(self) -> ToolResult:
        if not self.pending: return ToolResult(False, "Não há aprendizado aguardando confirmação.")
        item, self.pending = self.pending, None
        key = datetime.now().astimezone().isoformat(timespec="seconds")
        self.memories.set(item["type"], key, item["value"])
        entry = {"timestamp": key, "tipo": item["type"], "mudança": item["value"],
                 "origem": item.get("origin", "conversa"), "confirmado": True,
                 "arquivo": "Naty/05 - Memórias/Evolução da NATY.md"}
        if self.obsidian:
            self.obsidian.append_evolution(entry)
        return ToolResult(True, "Guardei essa informação com sua confirmação.", entry, type="learning_saved")

    def cancel(self) -> ToolResult:
        self.pending = None
        return ToolResult(True, "Tudo bem, não guardei essa informação.", type="learning_cancelled")
