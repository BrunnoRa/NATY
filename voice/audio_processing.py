from __future__ import annotations

from array import array
from dataclasses import dataclass

from voice.devices import audio_level


@dataclass(slots=True)
class GainSample:
    raw_level: float
    output_level: float
    gain: float


class AutomaticGain:
    """Ganho PCM16 leve, com gate para não transformar silêncio em ruído."""

    def __init__(self, max_gain: float = 12.0, enabled: bool = True,
                 target_level: float = 0.075, noise_floor: float = 0.00025):
        self.max_gain = max(1.0, min(20.0, float(max_gain)))
        self.enabled = enabled
        self.target_level = target_level
        self.noise_floor = noise_floor
        self.current_gain = min(4.0, self.max_gain) if enabled else self.max_gain

    def process(self, chunk: bytes) -> tuple[bytes, GainSample]:
        raw_level = audio_level(chunk)
        if self.enabled and raw_level > self.noise_floor:
            desired = max(1.0, min(self.max_gain, self.target_level / raw_level))
            self.current_gain = self.current_gain * 0.35 + desired * 0.65
        elif not self.enabled:
            self.current_gain = self.max_gain
        values = array("h")
        values.frombytes(chunk)
        gain = self.current_gain
        for index, value in enumerate(values):
            values[index] = max(-32768, min(32767, int(value * gain)))
        output = values.tobytes()
        return output, GainSample(raw_level, audio_level(output), gain)
