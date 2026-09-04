"""Compact always-on-top HUD used by the global shortcut."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable


class MiniWindow(tk.Toplevel):
    """Small text/voice entry surface that shares the main assistant callback."""

    BG = "#071017"
    PANEL = "#0d1b24"
    CYAN = "#4eeaff"
    TEXT = "#eaf8ff"
    MUTED = "#86a4b5"

    def __init__(
        self,
        master: tk.Misc,
        submit: Callable[[str, bool], str | None],
    ) -> None:
        super().__init__(master)
        self._submit = submit
        self.withdraw()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=self.BG, highlightbackground=self.CYAN, highlightthickness=1)
        self.geometry("360x190")

        self._orb = tk.Canvas(self, width=62, height=62, bg=self.BG, highlightthickness=0)
        self._orb.pack(pady=(18, 4))
        self._orb.create_oval(9, 9, 53, 53, fill="#123746", outline=self.CYAN, width=2)
        self._orb.create_oval(22, 22, 40, 40, fill=self.CYAN, outline="")

        self._status = tk.StringVar(value="Pronta")
        tk.Label(
            self,
            textvariable=self._status,
            bg=self.BG,
            fg=self.MUTED,
            font=("Segoe UI", 9),
        ).pack()

        entry_frame = tk.Frame(self, bg=self.PANEL, highlightbackground="#234454", highlightthickness=1)
        entry_frame.pack(fill="x", padx=18, pady=(10, 8))
        self.entry = tk.Entry(
            entry_frame,
            bg=self.PANEL,
            fg=self.TEXT,
            insertbackground=self.CYAN,
            relief="flat",
            font=("Segoe UI", 11),
        )
        self.entry.pack(fill="x", padx=10, pady=8)
        self.entry.bind("<Return>", self._on_submit)
        self.bind("<Escape>", lambda _event: self.hide())
        self.bind("<FocusOut>", self._on_focus_out)

    def show(self) -> None:
        self.update_idletasks()
        width, height = 360, 190
        x = max(0, (self.winfo_screenwidth() - width) // 2)
        y = max(0, (self.winfo_screenheight() - height) // 3)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.deiconify()
        self.lift()
        self.entry.focus_force()

    def hide(self) -> None:
        self.withdraw()

    def set_status(self, text: str) -> None:
        self._status.set(text)

    def _on_submit(self, _event: tk.Event | None = None) -> str:
        text = self.entry.get().strip()
        if not text:
            return "break"
        self.entry.delete(0, "end")
        self.set_status("Processando…")
        response = self._submit(text, False)
        if response:
            self.set_status(response)
        return "break"

    def _on_focus_out(self, _event: tk.Event) -> None:
        self.after(150, self._hide_if_unfocused)

    def _hide_if_unfocused(self) -> None:
        if self.focus_get() is None:
            self.hide()
