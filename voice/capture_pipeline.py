from __future__ import annotations

from array import array
from collections import deque
from dataclasses import dataclass
import math
import queue
import time
from collections.abc import Callable, Iterable

from voice.audio_processing import AutomaticGain


@dataclass(slots=True)
class CaptureMetrics:
    rms: float = 0.0
    peak: float = 0.0
    clipping: float = 0.0
    duration_seconds: float = 0.0
    speech_seconds: float = 0.0


@dataclass(slots=True)
class CapturedAudio:
    pcm: bytes
    sample_rate: int
    metrics: CaptureMetrics


def pcm_metrics(chunk: bytes) -> tuple[float, float, float]:
    samples = array("h"); samples.frombytes(chunk)
    if not samples: return 0.0, 0.0, 0.0
    rms = math.sqrt(sum(value * value for value in samples) / len(samples)) / 32768.0
    peak = max(abs(value) for value in samples) / 32768.0
    clipping = sum(1 for value in samples if abs(value) >= 32700) / len(samples)
    return min(1.0, rms), min(1.0, peak), clipping


class SpeechBuffer:
    """VAD energético com pre-roll; não corta o início e tolera pausas curtas."""

    def __init__(self, sample_rate: int = 16000, block_ms: int = 100, pre_roll_ms: int = 300,
                 end_silence_ms: int = 1100, max_utterance_seconds: int = 20, threshold: float = 0.012):
        self.sample_rate = sample_rate
        self.block_ms = block_ms
        self.pre_roll_blocks = max(1, math.ceil(pre_roll_ms / block_ms))
        self.end_silence_blocks = max(1, math.ceil(end_silence_ms / block_ms))
        self.max_blocks = max(1, math.ceil(max_utterance_seconds * 1000 / block_ms))
        self.threshold = threshold
        self._pre_roll: deque[bytes] = deque(maxlen=self.pre_roll_blocks)
        self._speech: list[bytes] = []
        self._started = False
        self._silent_blocks = 0
        self.finished = False
        self.levels: list[tuple[float, float, float]] = []

    @property
    def started(self) -> bool: return self._started

    def feed(self, chunk: bytes) -> bool:
        if self.finished: return True
        metrics = pcm_metrics(chunk); self.levels.append(metrics)
        voiced = metrics[0] >= self.threshold
        if not self._started:
            if voiced:
                self._started = True
                self._speech.extend(self._pre_roll)
                self._speech.append(chunk)
                self._pre_roll.clear()
            else:
                self._pre_roll.append(chunk)
            return False
        self._speech.append(chunk)
        self._silent_blocks = 0 if voiced else self._silent_blocks + 1
        self.finished = self._silent_blocks >= self.end_silence_blocks or len(self._speech) >= self.max_blocks
        return self.finished

    def result(self) -> bytes:
        if not self._started: return b""
        if self._silent_blocks:
            keep = max(0, len(self._speech) - self._silent_blocks + 1)
            return b"".join(self._speech[:keep])
        return b"".join(self._speech)


class MicrophoneCapture:
    def __init__(self, device: int = -1, sample_rate: int = 16000, gain: float = 12.0, automatic_gain: bool = True,
                 pre_roll_ms: int = 300, end_silence_ms: int = 1100, max_utterance_seconds: int = 20):
        self.device, self.sample_rate = device, sample_rate
        self.gain, self.automatic_gain = gain, automatic_gain
        self.pre_roll_ms, self.end_silence_ms = pre_roll_ms, end_silence_ms
        self.max_utterance_seconds = max_utterance_seconds

    def record(self, timeout: float = 8.0, on_level: Callable[[float], None] | None = None) -> CapturedAudio:
        import sounddevice as sd
        selected = self.device if self.device >= 0 else None
        try: native = int(sd.query_devices(selected, "input").get("default_samplerate", self.sample_rate))
        except Exception: native = self.sample_rate
        last_error = None
        for rate in dict.fromkeys((self.sample_rate, native)):
            try: return self._record_at_rate(sd, rate, timeout, on_level)
            except Exception as exc: last_error = exc
        assert last_error is not None
        raise last_error

    def _record_at_rate(self, sd, rate: int, timeout: float, on_level) -> CapturedAudio:
        chunks: queue.Queue[bytes] = queue.Queue()
        def callback(indata, frames, time_info, status): chunks.put(bytes(indata))
        kwargs = {"samplerate": rate, "blocksize": max(800, rate // 10), "dtype": "int16", "channels": 1, "callback": callback}
        if self.device >= 0: kwargs["device"] = self.device
        buffer = SpeechBuffer(rate, pre_roll_ms=self.pre_roll_ms, end_silence_ms=self.end_silence_ms,
                              max_utterance_seconds=self.max_utterance_seconds)
        gain = AutomaticGain(self.gain, self.automatic_gain)
        started = time.monotonic(); speech_started = None
        with sd.RawInputStream(**kwargs):
            while True:
                now = time.monotonic()
                if speech_started is None and now - started >= timeout: break
                if speech_started is not None and now - speech_started >= self.max_utterance_seconds: break
                try: chunk = chunks.get(timeout=.5)
                except queue.Empty: continue
                chunk, level = gain.process(chunk)
                if on_level: on_level(level.output_level)
                was_started = buffer.started
                if buffer.feed(chunk): break
                if not was_started and buffer.started: speech_started = time.monotonic()
        pcm = buffer.result()
        values = buffer.levels
        metrics = CaptureMetrics(
            rms=max((item[0] for item in values), default=0.0), peak=max((item[1] for item in values), default=0.0),
            clipping=max((item[2] for item in values), default=0.0), duration_seconds=(len(pcm) / 2 / rate),
            speech_seconds=(len(pcm) / 2 / rate),
        )
        return CapturedAudio(pcm, rate, metrics)
