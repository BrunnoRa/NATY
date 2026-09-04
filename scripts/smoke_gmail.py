from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

from config import Settings
from connectors.google.auth import GoogleAuth
from connectors.google.gmail import GmailConnector


def main() -> int:
    settings = Settings.load()
    if not settings.google_enabled:
        print("SKIP: Google não foi autorizado. Nenhuma conexão foi iniciada.")
        return 2
    gmail = GmailConnector(GoogleAuth.for_settings(settings))
    messages = gmail.search("in:inbox", max_results=3)
    print(gmail.summarize(messages))
    print("PASS: somente leitura; nenhum rascunho ou envio foi criado.")
    return 0


if __name__ == "__main__": raise SystemExit(main())
