from __future__ import annotations

import os
import webbrowser
from collections.abc import Callable

from core.models import ToolResult


class WindowsActionsTool:
    APPS = {
        "spotify": "spotify:",
        "obsidian": "obsidian://open",
        "youtube": "https://www.youtube.com/",
        "chatgpt": "https://chatgpt.com/",
        "gmail": "https://mail.google.com/",
        "vscode": "vscode://",
    }
    MEDIA_KEYS = {"next": 0xB0, "previous": 0xB1, "pause": 0xB3, "play": 0xB3, "volume_up": 0xAF, "volume_down": 0xAE}

    def __init__(self, opener: Callable[[str], None] | None = None, media_sender: Callable[[int], None] | None = None):
        self.opener = opener or self._open
        self.media_sender = media_sender or self._send_media_key
        self.delegation = None

    @staticmethod
    def _open(target: str) -> None:
        if target.startswith("http"):
            webbrowser.open(target)
        elif os.name == "nt":
            os.startfile(target)  # type: ignore[attr-defined]
        else:
            raise OSError("Launcher disponível somente no Windows.")

    @staticmethod
    def _send_media_key(key: int) -> None:
        if os.name != "nt":
            raise OSError("Controle de mídia disponível somente no Windows.")
        import ctypes
        ctypes.windll.user32.keybd_event(key, 0, 0, 0)
        ctypes.windll.user32.keybd_event(key, 0, 2, 0)

    def open_app(self, app: str) -> ToolResult:
        key = app.casefold().strip()
        target = self.APPS.get(key)
        if not target:
            return ToolResult(False, "Esse aplicativo não está na lista permitida.", type="app_error", error="app_not_allowed")
        try:
            self.opener(target)
            return ToolResult(True, f"Abri {key.title()}.", {"app": key}, type="app_opened")
        except OSError as exc:
            return ToolResult(False, f"Não consegui abrir {key.title()}: {exc}", {"app": key}, type="app_error", error=str(exc))

    def media(self, action: str) -> ToolResult:
        key = self.MEDIA_KEYS.get(action)
        labels = {"next": "Próxima música.", "previous": "Música anterior.", "pause": "Mídia pausada.",
                  "play": "Mídia retomada.", "volume_up": "Volume aumentado.", "volume_down": "Volume reduzido."}
        if key is None:
            return ToolResult(False, "Controle de mídia não reconhecido.", type="media_error", error="unknown_media_action")
        try:
            self.media_sender(key)
            return ToolResult(True, labels[action], {"action": action}, type=f"media_{action}")
        except OSError as exc:
            return ToolResult(False, f"Não consegui controlar a mídia: {exc}", type="media_error", error=str(exc))

    def delegate(self, text: str) -> ToolResult:
        try:
            if self.delegation:
                return self.delegation.prepare(text)
            self._copy_text(text)
            self.opener(self.APPS["chatgpt"])
            return ToolResult(True, "Abri o ChatGPT e copiei um pacote de contexto para você colar e aprofundar a análise.",
                              {"target": "chatgpt", "context": text}, type="delegation_ready")
        except OSError as exc:
            return ToolResult(False, f"Não consegui preparar a delegação: {exc}", type="delegation_error", error=str(exc))

    @staticmethod
    def _copy_text(text: str) -> None:
        if os.name != "nt":
            raise OSError("Delegação assistida disponível somente no Windows.")
        import ctypes
        kernel32, user32 = ctypes.windll.kernel32, ctypes.windll.user32
        encoded = text.encode("utf-16-le") + b"\x00\x00"
        handle = kernel32.GlobalAlloc(0x0002, len(encoded))
        if not handle:
            raise OSError("Falha ao reservar memória para o clipboard.")
        pointer = kernel32.GlobalLock(handle)
        ctypes.memmove(pointer, encoded, len(encoded))
        kernel32.GlobalUnlock(handle)
        if not user32.OpenClipboard(None):
            kernel32.GlobalFree(handle)
            raise OSError("Clipboard ocupado.")
        try:
            user32.EmptyClipboard()
            user32.SetClipboardData(13, handle)
        finally:
            user32.CloseClipboard()
