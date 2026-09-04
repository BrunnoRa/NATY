from __future__ import annotations

import json
from pathlib import Path
import queue
import time

from voice.stt_base import STTProvider


class VoskSTT(STTProvider):
    def __init__(self, model_path: str, sample_rate: int = 16000, unload_after_use: bool = True, device: int = -1):
        self.model_path, self.sample_rate, self.unload_after_use, self.device = model_path, sample_rate, unload_after_use, device
        self._model = None

    def available(self) -> bool:
        if not Path(self.model_path).is_dir(): return False
        try: import vosk, sounddevice  # noqa: F401
        except ImportError: return False
        return True

    def listen_once(self, timeout: float = 8.0) -> str:
        if not self.available(): raise RuntimeError("Vosk, sounddevice ou modelo pt-BR indisponível.")
        import sounddevice as sd
        from vosk import KaldiRecognizer, Model
        if self._model is None: self._model = Model(self.model_path)
        recognizer = KaldiRecognizer(self._model, self.sample_rate)
        audio: queue.Queue[bytes] = queue.Queue()
        def callback(indata, frames, time_info, status): audio.put(bytes(indata))
        started, last_partial = time.monotonic(), time.monotonic()
        try:
            kwargs = {"samplerate": self.sample_rate, "blocksize": 4000, "dtype": "int16", "channels": 1, "callback": callback}
            if self.device >= 0: kwargs["device"] = self.device
            with sd.RawInputStream(**kwargs):
                while time.monotonic() - started < timeout:
                    try: chunk = audio.get(timeout=0.5)
                    except queue.Empty: continue
                    if recognizer.AcceptWaveform(chunk):
                        text = json.loads(recognizer.Result()).get("text", "").strip()
                        if text: return text
                    else:
                        partial = json.loads(recognizer.PartialResult()).get("partial", "")
                        if partial: last_partial = time.monotonic()
                        if partial and time.monotonic() - last_partial > 1.2: break
                return json.loads(recognizer.FinalResult()).get("text", "").strip()
        finally:
            if self.unload_after_use: self.unload()

    def unload(self) -> None: self._model = None

    def transcribe_wav(self, path: str | Path) -> str:
        import wave
        if not self.available(): raise RuntimeError("Vosk ou modelo pt-BR indisponível.")
        from vosk import KaldiRecognizer, Model
        if self._model is None: self._model = Model(self.model_path)
        try:
            with wave.open(str(path), "rb") as audio:
                if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
                    raise ValueError("WAV deve ser mono PCM 16-bit.")
                recognizer = KaldiRecognizer(self._model, audio.getframerate())
                while chunk := audio.readframes(4000): recognizer.AcceptWaveform(chunk)
                return json.loads(recognizer.FinalResult()).get("text", "").strip()
        finally:
            if self.unload_after_use: self.unload()
