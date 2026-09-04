from __future__ import annotations

from pathlib import Path
import argparse
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

from config import Settings
from core.assistant import NatyAssistant
from ui.main_window import MainWindow


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--onboarding", action="store_true"); args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="naty-gui-smoke-", ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        settings = Settings(data_dir=str(root / "data"), log_dir=str(root / "logs"), first_run_completed=not args.onboarding, voice_enabled=False, tts_enabled=False, notifications_enabled=False)
        app = MainWindow(NatyAssistant(settings), use_tray=True)
        app.root.update_idletasks()
        print("GUI_READY", flush=True)
        app.root.after(2500, app.exit)
        app.run()
    print("GUI_CLOSED", flush=True)
    return 0


if __name__ == "__main__": raise SystemExit(main())
