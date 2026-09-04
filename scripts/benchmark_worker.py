from __future__ import annotations

import json
import logging
from pathlib import Path
import sys

from config import Settings
from core.assistant import NatyAssistant
from database.connection import Database
from core.models import ResearchItem
from research.search_provider import SearchProvider
from tools.research import ResearchTool


class BenchmarkSearchProvider(SearchProvider):
    def available(self) -> bool: return True
    def search(self, query: str, max_results: int = 5):
        return [ResearchItem(f"Resultado {n}", f"https://example.com/{n}", "Produto por R$ 899,90", source="example.com") for n in range(max_results)]


def main() -> None:
    root = Path(sys.argv[1])
    settings = Settings(data_dir=str(root / "data"), log_dir=str(root / "logs"), voice_enabled=False, tts_enabled=False, obsidian_enabled=False)
    app = NatyAssistant(settings, Database(root / "data" / "naty.db"))
    print("READY", flush=True)
    try:
        for line in sys.stdin:
            request = json.loads(line)
            if request.get("command") == "stop": break
            if request.get("command") == "research":
                tool = ResearchTool(app.db, BenchmarkSearchProvider())
                result = tool.search("monitor até 900 reais")
                print(json.dumps({"response": result.message}, ensure_ascii=False), flush=True); continue
            print(json.dumps({"response": app.handle(request["text"])}, ensure_ascii=False), flush=True)
    finally:
        logging.shutdown()


if __name__ == "__main__": main()
