from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import time
import wave

from voice.capture_pipeline import MicrophoneCapture
from voice.stt_base import STTProvider


class WhisperCppSTT(STTProvider):
    def __init__(self, executable: str, model_path: str, *, device: int = -1, language: str = "pt",
                 microphone_gain: float = 12.0, automatic_gain: bool = True, pre_roll_ms: int = 300,
                 end_silence_ms: int = 1100, max_utterance_seconds: int = 20):
        self.executable, self.model_path, self.language = executable, model_path, language
        self.capture = MicrophoneCapture(device=device, gain=microphone_gain, automatic_gain=automatic_gain,
            pre_roll_ms=pre_roll_ms, end_silence_ms=end_silence_ms, max_utterance_seconds=max_utterance_seconds)
        self.last_transcription = ""
        self.last_latency_ms: float | None = None
        self.last_capture_metrics = None

    def available(self) -> bool:
        return Path(self.executable).is_file() and Path(self.model_path).is_file()

    def transcribe_wav(self, path: str | Path) -> str:
        if not self.available(): raise RuntimeError("whisper.cpp ou modelo multilíngue indisponível.")
        started = time.perf_counter()
        result = subprocess.run([self.executable, "-m", self.model_path, "-f", str(path), "-l", self.language,
                                 "-nt", "-np", "-ng"], capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=120, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.last_latency_ms = (time.perf_counter() - started) * 1000
        if result.returncode: raise RuntimeError(result.stderr.strip() or "whisper.cpp falhou.")
        self.last_transcription = " ".join(line.strip() for line in result.stdout.splitlines() if line.strip()).strip()
        return self.last_transcription

    def listen_once(self, timeout: float = 8.0, on_level=None) -> str:
        captured = self.capture.record(timeout, on_level)
        self.last_capture_metrics = captured.metrics
        if not captured.pcm: return ""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp: path = Path(temp.name)
        try:
            with wave.open(str(path), "wb") as audio:
                audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(captured.sample_rate); audio.writeframes(captured.pcm)
            return self.transcribe_wav(path)
        finally:
            path.unlink(missing_ok=True)
