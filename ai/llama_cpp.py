from __future__ import annotations

import gc
from pathlib import Path
import threading
import time
from ai.base import AIProvider


class LlamaCppProvider(AIProvider):
    def __init__(self, model_path: str, threads: int = 4, context_size: int = 2048,
                 idle_unload_seconds: int = 90, max_ram_mb: int = 1800, min_available_ram_mb: int = 2200):
        self.model_path, self.threads, self.context_size = model_path, threads, context_size
        self.idle_unload_seconds, self.max_ram_mb, self.min_available_ram_mb = idle_unload_seconds, max_ram_mb, min_available_ram_mb
        self._model = None; self._lock = threading.RLock(); self._timer: threading.Timer | None = None; self.last_used = 0.0

    @staticmethod
    def available_ram_mb() -> int:
        try:
            import psutil
            return int(psutil.virtual_memory().available / 1024**2)
        except ImportError: return 0

    @property
    def loaded(self) -> bool: return self._model is not None

    def is_available(self) -> bool:
        if not Path(self.model_path).is_file(): return False
        try: import llama_cpp  # noqa: F401
        except ImportError: return False
        return True

    def load(self) -> None:
        with self._lock:
            if self._model is not None: return
            if not self.is_available(): raise RuntimeError("Modelo llama.cpp indisponível.")
            size_mb = Path(self.model_path).stat().st_size / 1024**2
            if size_mb > self.max_ram_mb: raise RuntimeError("O modelo excede o limite de memória configurado.")
            available = self.available_ram_mb()
            if available and available < self.min_available_ram_mb: raise RuntimeError("Memória livre insuficiente para carregar IA local com segurança.")
            from llama_cpp import Llama
            self._model = Llama(model_path=self.model_path, n_ctx=self.context_size, n_threads=self.threads, n_gpu_layers=0, verbose=False)

    def generate(self, prompt: str) -> str:
        with self._lock:
            self.load(); self.last_used = time.monotonic()
            result = self._model(prompt, max_tokens=256, temperature=0.2, stop=["<|im_end|>"])
            self._schedule_unload()
            return result["choices"][0]["text"].strip()

    def _schedule_unload(self) -> None:
        if self._timer: self._timer.cancel()
        self._timer = threading.Timer(max(1, self.idle_unload_seconds), self.unload); self._timer.daemon = True; self._timer.start()

    def unload(self) -> None:
        with self._lock:
            if self._timer: self._timer.cancel(); self._timer = None
            self._model = None; gc.collect()
