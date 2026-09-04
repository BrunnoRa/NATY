from __future__ import annotations

from pathlib import Path
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

from config import Settings
from core.assistant import NatyAssistant
from database.connection import Database


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="naty-conversation-smoke-") as temp:
        root = Path(temp)
        settings = Settings(data_dir=str(root / "data"), log_dir=str(root / "logs"), first_run_completed=True, voice_enabled=False, tts_enabled=False, notifications_enabled=False)
        assistant = NatyAssistant(settings, Database(root / "data" / "naty.db"))
        commands = [
            "cria tarefa organizar arquivos 15 minutos",
            "cria tarefa revisar projeto 90 minutos",
            "estou cansada hoje",
            "lembre que eu prefiro foco pela manhã",
            "o que você lembra sobre mim?",
            "adiciona café e leite na lista de compras",
            "indo ao mercado",
        ]
        responses = []
        for command in commands:
            response = assistant.handle(command); responses.append(response)
            print(f"> {command}\n{response}\n")
        checks = ["organizar arquivos" in responses[2].casefold(), "foco pela manhã" in responses[4].casefold(), "2 item" in responses[6].casefold()]
        print("PASS" if all(checks) else "FAIL")
        assistant.close()
        return 0 if all(checks) else 2


if __name__ == "__main__": raise SystemExit(main())
