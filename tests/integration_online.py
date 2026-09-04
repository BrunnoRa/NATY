"""Execute manualmente com internet: python -m tests.integration_online"""
from pathlib import Path
import tempfile

from database.connection import Database
from database.migrations import migrate
from tools.research import ResearchTool


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as temp:
        db = Database(Path(temp) / "test.db"); migrate(db)
        result = ResearchTool(db).search("site:python.org Python", read_pages=False)
        print(result.message)
        raise SystemExit(0 if result.ok and result.sources else 1)
