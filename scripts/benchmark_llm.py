from __future__ import annotations

import json
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

from ai.llama_cpp import LlamaCppProvider
from config import Settings


def main() -> int:
    settings = Settings.load()
    provider = LlamaCppProvider(
        settings.ai_model_path, settings.ai_threads, settings.ai_context_size,
        settings.ai_idle_unload_seconds, settings.ai_max_ram_mb,
        settings.ai_min_available_ram_mb,
    )
    if not provider.is_available():
        print(json.dumps({"available": False, "reason": "modelo ou llama-cpp-python indisponível"}, ensure_ascii=False))
        return 2
    try:
        import psutil
        process = psutil.Process(); before = process.memory_info().rss
    except ImportError:
        process = None; before = 0
    started = time.perf_counter()
    answer = provider.generate("Responda somente com a palavra: pronta")
    elapsed = time.perf_counter() - started
    after = process.memory_info().rss if process else 0
    report = {
        "available": True, "model": str(Path(settings.ai_model_path).name),
        "load_and_generation_seconds": round(elapsed, 3),
        "rss_delta_mib": round((after - before) / 1024**2, 2) if process else None,
        "response_chars": len(answer), "cpu_only": True,
    }
    provider.unload()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__": raise SystemExit(main())
