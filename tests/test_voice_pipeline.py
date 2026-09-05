from array import array
import unittest

from voice.capture_pipeline import SpeechBuffer, pcm_metrics
from voice.vosk_stt import VoskSTT


def pcm(level: int, milliseconds: int = 100, rate: int = 16000) -> bytes:
    return array("h", [level] * (rate * milliseconds // 1000)).tobytes()


class VoicePipelineTests(unittest.TestCase):
    def test_empty_vosk_path_is_not_current_directory_model(self):
        self.assertFalse(VoskSTT("").available())

    def test_pre_roll_preserves_audio_before_voice(self):
        buffer = SpeechBuffer(pre_roll_ms=300, end_silence_ms=1100)
        for _ in range(3): buffer.feed(pcm(100))
        buffer.feed(pcm(5000))
        self.assertEqual(len(buffer.result()), 4 * len(pcm(0)))

    def test_natural_short_pause_does_not_finish(self):
        buffer = SpeechBuffer(end_silence_ms=1100)
        buffer.feed(pcm(5000))
        for _ in range(8): self.assertFalse(buffer.feed(pcm(0)))
        self.assertFalse(buffer.finished)
        buffer.feed(pcm(5000))
        self.assertFalse(buffer.finished)

    def test_end_silence_finishes_after_1100_ms(self):
        buffer = SpeechBuffer(end_silence_ms=1100)
        buffer.feed(pcm(5000))
        for _ in range(10): self.assertFalse(buffer.feed(pcm(0)))
        self.assertTrue(buffer.feed(pcm(0)))

    def test_metrics_report_peak_rms_and_clipping(self):
        rms, peak, clipping = pcm_metrics(array("h", [0, 32767, -32768, 100]).tobytes())
        self.assertGreater(rms, .6); self.assertEqual(peak, 1.0); self.assertEqual(clipping, .5)
