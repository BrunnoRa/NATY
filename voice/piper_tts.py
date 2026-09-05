from __future__ import annotations

from pathlib import Path
import os
import subprocess
import tempfile
import threading
import time
import wave
import winsound

from voice.tts_base import TTSProvider


class PiperTTS(TTSProvider):
    def __init__(self, executable: str = "", model_path: str = "", config_path: str = ""):
        self.executable, self.model_path = executable, model_path
        self.config_path = config_path or (str(model_path) + ".json" if model_path else "")
        self._process = None
        self._lock = threading.RLock()
        self._cancel = threading.Event()

    def configure(self, executable: str, model_path: str, config_path: str = "") -> "PiperTTS":
        self.executable, self.model_path = executable, model_path
        self.config_path = config_path or str(model_path) + ".json"
        return self

    def available(self) -> bool:
        return Path(self.executable).is_file() and Path(self.model_path).is_file() and Path(self.config_path).is_file()

    def load(self) -> None:
        if not self.available():
            raise RuntimeError("Runtime, modelo ou configuração do Piper indisponível.")

    def synthesize(self, text: str, output_path: str | Path | None = None) -> Path:
        self.load()
        if not text.strip():
            raise ValueError("Texto vazio para síntese.")
        if output_path:
            output = Path(output_path)
        else:
            descriptor, temporary = tempfile.mkstemp(suffix=".wav")
            os.close(descriptor)
            output = Path(temporary)
        output.parent.mkdir(parents=True, exist_ok=True)
        self._cancel.clear()
        command = [self.executable, "--model", self.model_path, "--config", self.config_path, "--output_file", str(output)]
        process = None
        try:
            with self._lock:
                self._process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                                 stderr=subprocess.PIPE, text=True, encoding="utf-8",
                                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                process = self._process
            _, error = process.communicate(text, timeout=max(30, len(text) // 4))
            if self._cancel.is_set():
                raise RuntimeError("Síntese Piper cancelada.")
            if process.returncode:
                raise RuntimeError((error or "Piper falhou ao sintetizar a resposta.").strip())
            if not output.is_file() or output.stat().st_size < 44:
                raise RuntimeError("Piper não produziu um WAV válido.")
            return output
        except subprocess.TimeoutExpired as exc:
            process.kill(); process.communicate()
            raise RuntimeError("Piper excedeu o tempo limite de síntese.") from exc
        finally:
            with self._lock:
                if process is not None and self._process is process:
                    self._process = None

    def speak(self, text: str) -> None:
        if not text.strip(): return
        descriptor, temporary = tempfile.mkstemp(suffix=".wav")
        os.close(descriptor)
        output = Path(temporary)
        try:
            self.synthesize(text, output)
            with wave.open(str(output), "rb") as audio:
                duration = audio.getnframes() / max(1, audio.getframerate())
            winsound.PlaySound(str(output), winsound.SND_FILENAME | winsound.SND_ASYNC)
            deadline = time.monotonic() + duration + 0.15
            while time.monotonic() < deadline and not self._cancel.wait(0.04):
                pass
        finally:
            try: winsound.PlaySound(None, winsound.SND_PURGE)
            except RuntimeError: pass
            output.unlink(missing_ok=True)

    def stop(self) -> None:
        self._cancel.set()
        with self._lock:
            process = self._process
        if process is not None and process.poll() is None:
            process.terminate()
        try: winsound.PlaySound(None, winsound.SND_PURGE)
        except RuntimeError: pass

    def unload(self) -> None: self.stop()
