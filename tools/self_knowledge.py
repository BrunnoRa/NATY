from __future__ import annotations

import unicodedata

from core.models import ToolResult
from version import __version__


def _plain(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", value.casefold()) if unicodedata.category(c) != "Mn")


class SelfKnowledgeTool:
    def __init__(self, registry, assistant):
        self.registry, self.assistant = registry, assistant

    def answer(self, query: str = "", show_all: bool = False) -> ToolResult:
        plain = _plain(query)
        skills = self.registry.status()
        if "versao" in plain:
            return ToolResult(True, f"Estou na versão {__version__}.", {"version": __version__}, type="self_status")
        if "google" in plain:
            state = self.assistant.google.auth.status().get("state", "not_configured")
            message = "O Google está conectado." if state == "connected" else "O Google ainda não está conectado."
            return ToolResult(True, message, {"component": "google", "state": state}, type="self_status")
        if "whisper" in plain:
            item = next(item for item in self.assistant.diagnostics.run()["items"] if item["name"] == "Whisper")
            return ToolResult(True, item["message"], {"component": "whisper", "state": item["state"]}, type="self_status")
        if "quais skills" in plain or "skills ainda nao" in plain:
            gaps = self.assistant.skill_gaps.list()
            if not gaps: return ToolResult(True, "Nenhuma capacidade ausente foi confirmada por você até agora.", {"gaps": []}, type="skill_gaps")
            return ToolResult(True, "Capacidades desejadas registradas: " + "; ".join(item["request_text"] for item in gaps[:8]) + ".",
                              {"gaps": gaps}, type="skill_gaps")
        matched = next((skill for skill in skills if any(_plain(alias) in plain for alias in (skill["name"], *skill["aliases"]))), None)
        if matched and any(term in plain for term in ("consegue", "pode", "sabe")):
            detail = matched["description"]
            if matched["requires_credentials"]: detail += " Requer credenciais configuradas."
            if matched["requires_network"]: detail += " Requer internet."
            return ToolResult(True, f"Sim. {detail}", {"skill": matched}, type="capability_status")
        categories = {skill["category"] for skill in skills}
        message = (f"Tenho {len(skills)} Skills ativas em {len(categories)} categorias. Posso organizar tarefas e lembretes, "
                   "pesquisar com fontes, consultar memória e Obsidian, abrir aplicativos, controlar mídia, criar modos e "
                   "automações, resumir seu dia e monitorar o computador.")
        return ToolResult(True, message, {"skills": skills}, type="capabilities",
                          ui_hint={"mode": "context" if show_all else "brain", "panel": "capabilities" if show_all else "none", "title": "Capacidades"})
