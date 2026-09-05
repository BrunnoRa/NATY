from __future__ import annotations

import argparse

from config import Settings
from core.assistant import NatyAssistant
from ipc.handler import CoreRequestHandler
from ipc.windows_pipe import WindowsNamedPipeServer


def main() -> int:
    parser = argparse.ArgumentParser(description="NATY Core host para o Desktop Windows")
    parser.add_argument("--pipe", default="Naty.Core.v1")
    args = parser.parse_args()
    assistant = NatyAssistant(Settings.load())
    if assistant.settings.notifications_enabled:
        assistant.start_scheduler()
    handler = CoreRequestHandler(assistant)
    server = WindowsNamedPipeServer(args.pipe, handler, assistant.logger)
    assistant.logger.info("Core IPC iniciado em %s", server.path)
    try:
        server.serve_forever()
        return 0
    finally:
        assistant.close()


if __name__ == "__main__":
    raise SystemExit(main())
