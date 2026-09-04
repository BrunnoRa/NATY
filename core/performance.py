from __future__ import annotations

import os


class PerformanceMonitor:
    def __init__(self):
        self.process = None
        try:
            import psutil
            self.process = psutil.Process(os.getpid()); self.process.cpu_percent(None)
        except ImportError: pass

    def snapshot(self, ai_loaded: bool = False, stt_loaded: bool = False) -> dict:
        if not self.process: return {"rss_mb": None, "cpu": None, "ai_loaded": ai_loaded, "stt_loaded": stt_loaded}
        return {"rss_mb": round(self.process.memory_info().rss/1024**2,1), "cpu": round(self.process.cpu_percent(None),1),
                "ai_loaded": ai_loaded, "stt_loaded": stt_loaded}
