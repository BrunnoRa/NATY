from __future__ import annotations

from core.models import ToolResult


class ActiveContextTool:
    DISPLAY_NAMES = {
        "code": "Visual Studio Code",
        "chrome": "Google Chrome",
        "msedge": "Microsoft Edge",
        "explorer": "Explorador de Arquivos",
        "obsidian": "Obsidian",
        "spotify": "Spotify",
    }

    def __init__(self, context):
        self.context = context

    @classmethod
    def _display_name(cls, process: str) -> str:
        clean = process.removesuffix(".exe")
        return cls.DISPLAY_NAMES.get(clean.casefold(), clean or "aplicativo")

    def show(self) -> ToolResult:
        app = self.context.active_app
        if not app:
            return ToolResult(False, "Não consegui identificar uma janela usada antes da NATY nesta sessão.",
                              type="active_context", error="active_context_unavailable")
        name = self._display_name(app["process_name"])
        title = app.get("window_title", "")
        detail = f" — {title}" if title and title.casefold() != name.casefold() else ""
        return ToolResult(True, f"Antes de abrir a NATY, você estava em {name}{detail}.", {"active_app": app},
                          type="active_context", ui_hint={"mode": "context", "panel": "active_context", "title": "Contexto atual"})

    def return_to_previous(self, project_only: bool = False) -> ToolResult:
        app = self.context.active_app
        if not app or not app.get("window_handle"):
            return ToolResult(False, "Não tenho uma janela anterior segura para reativar.",
                              type="active_context_activate", error="active_context_unavailable")
        name = self._display_name(app["process_name"])
        if project_only and app["process_name"].casefold().removesuffix(".exe") not in {"code", "devenv", "obsidian"}:
            return ToolResult(False, "Não identifiquei um projeto aberto na janela anterior; não vou inventar um caminho.",
                              {"active_app": app}, type="active_context_activate", error="project_context_unavailable")
        return ToolResult(True, f"Voltando para {name}.",
                          {"active_app": app, "action": "activate_window", "window_handle": app["window_handle"]},
                          type="active_context_activate")
