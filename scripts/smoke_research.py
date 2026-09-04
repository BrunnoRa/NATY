from __future__ import annotations

from pathlib import Path
import argparse
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import Database
from database.migrations import migrate
from research.ddgs_provider import DDGSProvider
from tools.research import ResearchTool


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--query", default="site:python.org Python documentation"); parser.add_argument("--compare", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="naty-research-smoke-") as temp:
        db = Database(Path(temp) / "smoke-research.db"); migrate(db)
        result = ResearchTool(db, DDGSProvider(), max_results=3).search(args.query, compare=args.compare, read_pages=args.compare)
        print(result.message)
        for source in result.sources: print(f"- {source['title']}: {source['url']}")
        return 0 if result.ok and result.sources else 2


if __name__ == "__main__": raise SystemExit(main())
