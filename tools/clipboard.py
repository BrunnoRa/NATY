from __future__ import annotations

from datetime import datetime
import os
import re

from core.models import ToolResult


class ClipboardTextProvider:
    """Reads Unicode text only when explicitly called by a skill."""

    def read(self) -> str:
        if os.name != "nt":
            raise OSError("Clipboard disponível somente no Windows.")
        import ctypes
        user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
        if not user32.OpenClipboard(None):
            raise OSError("A área de transferência está ocupada.")
        try:
            handle = user32.GetClipboardData(13)  # CF_UNICODETEXT
            if not handle:
                return ""
            pointer = kernel32.GlobalLock(handle)
            if not pointer:
                return ""
            try:
                return ctypes.wstring_at(pointer)
            finally:
                kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()


class ClipboardTool:
    def __init__(self, provider=None, research=None, obsidian=None):
        self.provider = provider or ClipboardTextProvider()
        self.research, self.obsidian = research, obsidian

    def _text(self) -> tuple[str, ToolResult | None]:
        try:
            text = self.provider.read().strip()
        except OSError as exc:
            return "", ToolResult(False, f"Não consegui ler a área de transferência: {exc}", type="clipboard_error")
        if not text:
            return "", ToolResult(False, "A área de transferência não contém texto.", type="clipboard_empty")
        return text, None

    def show(self) -> ToolResult:
        text, error = self._text()
        if error: return error
        preview = text if len(text) <= 900 else text[:897].rstrip() + "..."
        return ToolResult(True, f"Você copiou: {preview}", {"text": text}, type="clipboard_text",
                          ui_hint={"mode": "context", "panel": "clipboard", "title": "Área de transferência"})

    def summarize(self) -> ToolResult:
        text, error = self._text()
        if error: return error
        compact = re.sub(r"\s+", " ", text).strip()
        parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", compact) if part.strip()]
        summary = " ".join(parts[:3])[:600].rstrip()
        if len(compact) > len(summary): summary = summary.rstrip(".") + "…"
        return ToolResult(True, f"Resumo do que foi copiado: {summary}", {"text": text, "summary": summary},
                          type="clipboard_summary", ui_hint={"mode": "context", "panel": "clipboard", "title": "Resumo do Clipboard"})

    def research_text(self) -> ToolResult:
        text, error = self._text()
        if error: return error
        if not self.research: return ToolResult(False, "A pesquisa não está disponível.", type="clipboard_error")
        return self.research.search(text[:500])

    def save_to_obsidian(self) -> ToolResult:
        text, error = self._text()
        if error: return error
        if not self.obsidian or not self.obsidian.available:
            return ToolResult(False, "Configure a pasta gerenciada da NATY no Obsidian primeiro.", type="clipboard_error")
        now = datetime.now().astimezone()
        path = self.obsidian.save_note("Notas", f"Clipboard - {now:%Y-%m-%d %H%M%S}", text)
        return ToolResult(True, f"Salvei o texto copiado no Obsidian: {path}.", {"path": str(path)}, type="clipboard_saved")
