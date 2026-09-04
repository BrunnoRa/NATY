from __future__ import annotations

import logging
import gc
from pathlib import Path
import tempfile
import time
import unittest

from config import Settings
from database.connection import Database
from database.migrations import migrate


class TempDatabaseTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = Database(self.root / "naty.db")
        migrate(self.db)

    def tearDown(self):
        logger = logging.getLogger("naty")
        for handler in logger.handlers[:]:
            handler.close(); logger.removeHandler(handler)
        # Windows/SQLite pode recriar ou liberar arquivos WAL entre o scan e o
        # rmdir. Repetir uma limpeza já autorizada evita falso negativo WinError 145.
        for attempt in range(3):
            try:
                self.temp.cleanup()
                break
            except OSError:
                if attempt == 2:
                    raise
                gc.collect(); time.sleep(0.05)

    def settings(self, **overrides) -> Settings:
        values = {"data_dir": str(self.root / "data"), "log_dir": str(self.root / "logs"), "voice_enabled": False, "tts_enabled": False}
        values.update(overrides)
        return Settings(**values)
