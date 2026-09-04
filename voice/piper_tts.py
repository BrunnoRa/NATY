from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import winsound

from voice.tts_base import TTSProvider


class PiperTTS(TTSProvider):
    def __init__(self, executable: str = "piper", model_path: str = ""):
        self.executable, self.model_path = executable, model_path
    def available(self) -> bool: return Path(self.model_path).is_file()
    def speak(self, text: str) -> None:
        if not self.available(): raise RuntimeError("Modelo Piper indisponível.")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp: output = temp.name
        try:
            subprocess.run([self.executable, "--model", self.model_path, "--output_file", output], input=text,
                           text=True, check=True, timeout=60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            winsound.PlaySound(output, winsound.SND_FILENAME)
        finally:
            Path(output).unlink(missing_ok=True)
