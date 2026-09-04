from __future__ import annotations

import json
from pathlib import Path
import queue
import time
from collections.abc import Callable

from voice.stt_base import STTProvider
from voice.devices import audio_level
from voice.audio_processing import AutomaticGain


class VoskSTT(STTProvider):
    def __init__(self, model_path: str, sample_rate: int = 16000, unload_after_use: bool = True, device: int = -1,
                 microphone_gain: float = 12.0, automatic_gain: bool = True):
        self.model_path, self.sample_rate, self.unload_after_use, self.device = model_path, sample_rate, unload_after_use, device
        self.microphone_gain, self.automatic_gain = microphone_gain, automatic_gain
        self._model = None
        self.last_transcription = ""
        self.last_latency_ms: float | None = None
        self.last_sample_rate = sample_rate
        self.last_raw_level = 0.0
        self.last_output_level = 0.0
        self.last_gain = 1.0

    def available(self) -> bool:
        if not Path(self.model_path).is_dir(): return False
        try: import vosk, sounddevice  # noqa: F401
        except ImportError: return False
        return True

    def diagnostics(self) -> dict:
        model = Path(self.model_path)
        try:
            import vosk  # noqa: F401
            vosk_installed = True
        except ImportError:
            vosk_installed = False
        try:
            import sounddevice  # noqa: F401
            sounddevice_installed = True
        except ImportError:
            sounddevice_installed = False
        return {"vosk_installed": vosk_installed, "sounddevice_installed": sounddevice_installed,
                "model_path": str(model), "model_available": model.is_dir(),
                "last_transcription": self.last_transcription, "last_latency_ms": self.last_latency_ms,
                "sample_rate": self.last_sample_rate, "raw_level": self.last_raw_level,
                "output_level": self.last_output_level, "gain": self.last_gain}

    def _open_stream(self, sd, callback):
        rates = [self.sample_rate]
        try:
            selected = self.device if self.device >= 0 else None
            default_rate = int(sd.query_devices(selected, "input").get("default_samplerate", self.sample_rate))
            if default_rate not in rates: rates.append(default_rate)
        except Exception:
            pass
        last_error = None
        for rate in rates:
            kwargs = {"samplerate": rate, "blocksize": max(800, rate // 10), "dtype": "int16", "channels": 1, "callback": callback}
            if self.device >= 0: kwargs["device"] = self.device
            try:
                return sd.RawInputStream(**kwargs), rate
            except Exception as exc:
                last_error = exc
        assert last_error is not None
        raise last_error

    def listen_once(self, timeout: float = 8.0, on_level: Callable[[float], None] | None = None) -> str:
        if not self.available(): raise RuntimeError("Vosk, sounddevice ou modelo pt-BR indisponível.")
        import sounddevice as sd
        from vosk import KaldiRecognizer, Model
        if self._model is None: self._model = Model(self.model_path)
        audio: queue.Queue[bytes] = queue.Queue()
        def callback(indata, frames, time_info, status): audio.put(bytes(indata))
        started = time.monotonic()
        try:
            stream, actual_rate = self._open_stream(sd, callback)
            self.last_sample_rate = actual_rate
            recognizer = KaldiRecognizer(self._model, actual_rate)
            gain = AutomaticGain(self.microphone_gain, self.automatic_gain)
            last_partial_text, last_voice_at, speech_seen = "", time.monotonic(), False
            with stream:
                while time.monotonic() - started < timeout:
                    try: chunk = audio.get(timeout=0.5)
                    except queue.Empty: continue
                    chunk, levels = gain.process(chunk)
                    self.last_raw_level, self.last_output_level, self.last_gain = levels.raw_level, levels.output_level, levels.gain
                    if on_level: on_level(levels.output_level)
                    now = time.monotonic()
                    if audio_level(chunk) >= 0.012:
                        last_voice_at, speech_seen = now, True
                    if recognizer.AcceptWaveform(chunk):
                        text = json.loads(recognizer.Result()).get("text", "").strip()
                        if text:
                            self.last_transcription = text
                            return text
                    else:
                        partial = json.loads(recognizer.PartialResult()).get("partial", "")
                        if partial and partial != last_partial_text:
                            last_partial_text, last_voice_at, speech_seen = partial, now, True
                    if speech_seen and now - last_voice_at > 1.2:
                        break
                text = json.loads(recognizer.FinalResult()).get("text", "").strip()
                self.last_transcription = text
                return text
        finally:
            self.last_latency_ms = (time.monotonic() - started) * 1000
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
