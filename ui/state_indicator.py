from tkinter import ttk


COLORS = {"IDLE": "#6b8ca4", "LISTENING": "#4df0b4", "TRANSCRIBING": "#55e6ff", "PROCESSING": "#55e6ff", "RETRIEVING": "#9b8cff", "RESEARCHING": "#9b8cff", "GMAIL": "#ffcf66", "SPEAKING": "#55e6ff", "ERROR": "#ff6680"}


class StateIndicator(ttk.Label):
    def set_state(self, state) -> None:
        value = getattr(state, "value", str(state))
        self.configure(text=f"● {value}", foreground=COLORS.get(value, "#6b7280"))
