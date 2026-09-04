from __future__ import annotations

import ctypes
import os
import threading
from ctypes import wintypes


MODIFIERS = {"ALT": 0x0001, "CTRL": 0x0002, "SHIFT": 0x0004, "WIN": 0x0008}
KEYS = {"SPACE": 0x20, "ENTER": 0x0D, "TAB": 0x09}
WM_HOTKEY, WM_QUIT = 0x0312, 0x0012


def parse_hotkey(value: str) -> tuple[int, int]:
    parts = [p.strip().upper() for p in value.split("+") if p.strip()]
    if len(parts) < 2: raise ValueError("Hotkey deve conter modificador e tecla.")
    modifiers = 0
    for part in parts[:-1]:
        if part not in MODIFIERS: raise ValueError(f"Modificador inválido: {part}")
        modifiers |= MODIFIERS[part]
    key_name = parts[-1]
    key = KEYS.get(key_name, ord(key_name) if len(key_name) == 1 else 0)
    if not key: raise ValueError(f"Tecla inválida: {key_name}")
    return modifiers, key


class GlobalHotkey:
    def __init__(self, hotkey: str, callback):
        self.modifiers, self.key = parse_hotkey(hotkey)
        self.callback, self._thread, self._thread_id = callback, None, None

    def start(self) -> bool:
        if os.name != "nt": return False
        if self._thread and self._thread.is_alive(): return True
        self._thread = threading.Thread(target=self._run, name="NatyHotkey", daemon=True); self._thread.start()
        return True

    def _run(self) -> None:
        user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
        self._thread_id = kernel32.GetCurrentThreadId()
        if not user32.RegisterHotKey(None, 1, self.modifiers, self.key): return
        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY:
                    try: self.callback()
                    except Exception: pass
        finally: user32.UnregisterHotKey(None, 1)

    def stop(self) -> None:
        if os.name == "nt" and self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread and self._thread.is_alive(): self._thread.join(timeout=2)
