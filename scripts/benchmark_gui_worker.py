from __future__ import annotations

import logging
from pathlib import Path
import sys

from config import Settings
from core.assistant import NatyAssistant
from core.models import AppState
from ui.main_window import MainWindow


def main() -> None:
    root = Path(sys.argv[1])
    settings = Settings(data_dir=str(root / "gui-data"), log_dir=str(root / "gui-logs"),
                        voice_enabled=False, tts_enabled=False, notifications_enabled=False,
                        first_run_completed=True)
    app = MainWindow(NatyAssistant(settings), use_tray=True)
    print("READY", flush=True)
    def graph_active():
        app._set_state(AppState.PROCESSING); print("GRAPH_ACTIVE", flush=True)
    def minimized():
        app._set_state(AppState.IDLE); app.hide(); print("MINIMIZED", flush=True)
    app.root.after(2500, graph_active)
    app.root.after(5000, minimized)
    app.root.after(7500, app.exit)
    try: app.run()
    finally: logging.shutdown()


if __name__ == "__main__": main()
