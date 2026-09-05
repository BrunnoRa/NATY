from __future__ import annotations

import unittest

from config import Settings
from voice.controller import VoiceController


class FakeVoiceManager:
    microphone = {"id": 19, "name": "Realtek"}

    class STT: pass
    class TTS:
        def unload(self): pass

    stt = STT()
    tts = TTS()

    def __init__(self):
        self.heard = self.failed = self.state = None
        self.stopped = False

    def start_session(self, heard, failed, level, state):
        self.heard, self.failed, self.state = heard, failed, state
        level(0.25)

    def respond_and_follow_up(self, answer, heard, failed, closed, state, level):
        state("SPEAKING")
        self.answer = answer
        self.closed = closed

    def stop_session(self): self.stopped = True


class VoiceControllerTests(unittest.TestCase):
    def test_voice_runs_through_processing_and_speaking(self):
        manager = FakeVoiceManager()
        controller = VoiceController(Settings(voice_enabled=True),
                                     lambda text: {"text": f"Resposta: {text}", "ui": {"panel": "none"}}, manager)
        started = controller.start()
        self.assertEqual(started["state"], "LISTENING")
        self.assertEqual(started["microphone"]["id"], 19)
        manager.state("TRANSCRIBING")
        self.assertEqual(controller.snapshot()["state"], "TRANSCRIBING")
        manager.heard("olá")
        speaking = controller.snapshot()
        self.assertEqual(speaking["state"], "SPEAKING")
        self.assertEqual(speaking["transcription"], "olá")
        self.assertEqual(speaking["response"], "Resposta: olá")
        manager.closed()
        self.assertEqual(controller.snapshot()["state"], "IDLE")

    def test_start_interrupts_active_session(self):
        manager = FakeVoiceManager()
        controller = VoiceController(Settings(voice_enabled=True), lambda _: {"text": "ok"}, manager)
        controller.start(); controller.start()
        self.assertTrue(manager.stopped)


if __name__ == "__main__": unittest.main()
