from __future__ import annotations

import re
from typing import Callable

from core.models import ToolResult


SECRET_PATTERNS = (
    re.compile(r"(?i)\b(api[_ -]?key|token|senha|password|secret)\b\s*[:=]\s*\S+"),
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]{12,}|AIza[A-Za-z0-9_-]{20,})\b"),
)


def redact_secrets(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[SEGREDO REMOVIDO]", text)
    return text


class ContextPackBuilder:
    def __init__(self, retriever, session_context=None, max_chars: int = 6000):
        self.retriever, self.session_context, self.max_chars = retriever, session_context, max_chars

    def build(self, question: str) -> str:
        pack = self.retriever.retrieve(question)
        local = redact_secrets(pack.as_prompt_data())
        structured = pack.structured if isinstance(pack.structured, dict) else {}
        project = structured.get("project", {})
        project_text = project.get("name", "Não identificado") if isinstance(project, dict) else "Não identificado"
        turns = list(getattr(self.session_context, "turns", ())) if self.session_context else []
        session_text = "\n".join(
            f"Usuário: {redact_secrets(str(turn.get('user', '')))[:300]}\nNATY: {redact_secrets(str(turn.get('response', '')))[:300]}"
            for turn in turns[-3:]
        ) or "Nenhum turno anterior relevante."
        active_app = getattr(self.session_context, "active_app", None) if self.session_context else None
        active_text = "Não informado."
        if isinstance(active_app, dict):
            active_text = f"{str(active_app.get('process_name', ''))[:120]} — {str(active_app.get('window_title', ''))[:240]}".strip(" —")
        prompt = (
            "# Contexto preparado pela NATY\n\n"
            f"Objetivo:\nAnalisar com profundidade o pedido abaixo.\n\n"
            f"Contexto relevante:\n{local or 'Nenhum dado local relevante encontrado.'}\n\n"
            "Preferências relevantes:\nResponda em português, de forma prática e sem inventar dados pessoais.\n\n"
            f"Projeto relacionado:\n{project_text}\n\n"
            f"Contexto recente da sessão:\n{session_text}\n\n"
            f"Aplicativo ativo (somente quando útil):\n{redact_secrets(active_text)}\n\n"
            f"Pergunta:\n{redact_secrets(question)}"
        )
        return prompt[:self.max_chars]


class ChatGPTWebProvider:
    def __init__(self, retriever, copier: Callable[[str], None], opener: Callable[[str], None], session_context=None):
        self.builder = ContextPackBuilder(retriever, session_context)
        self.copier, self.opener = copier, opener

    def prepare(self, question: str) -> ToolResult:
        context = self.builder.build(question)
        self.copier(context)
        self.opener("https://chatgpt.com/")
        return ToolResult(True, "Esse pedido se beneficia de uma análise mais profunda. Preparei o contexto e abri o ChatGPT.",
                          {"target": "chatgpt", "context": context}, type="delegation_ready",
                          ui_hint={"mode": "context", "panel": "delegation", "title": "Delegação externa"})


class ExternalResultImporter:
    LINK = re.compile(r"https?://[^\s)>\]]+")

    def analyze(self, text: str) -> dict:
        clean = redact_secrets(text.strip())[:12000]
        lines = [re.sub(r"^\s*[-*\d.)]+\s*", "", line).strip() for line in clean.splitlines() if line.strip()]
        decisions, preferences, tasks, facts = [], [], [], []
        for line in lines:
            plain = line.casefold()
            if any(word in plain for word in ("decisão", "decidi", "recomendo", "recomendação")): decisions.append(line)
            elif any(word in plain for word in ("preferência", "prefiro", "priorize")): preferences.append(line)
            elif any(word in plain for word in ("tarefa", "próximo passo", "ação:", "todo")): tasks.append(line)
            elif not self.LINK.fullmatch(line): facts.append(line)
        return {"decisions": decisions[:10], "facts": facts[:20], "preferences": preferences[:10],
                "tasks": tasks[:10], "links": list(dict.fromkeys(self.LINK.findall(clean)))[:20]}

    def result(self, text: str) -> ToolResult:
        data = self.analyze(text)
        count = sum(len(value) for value in data.values())
        return ToolResult(bool(count), f"Encontrei {count} informações úteis. Deseja salvá-las?" if count else
                          "Não encontrei informações estruturadas para importar.", data,
                          type="external_import_preview", ui_hint={"mode": "context", "panel": "learning", "title": "Importar resultado externo"})
