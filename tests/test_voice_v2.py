import json
from array import array
from pathlib import Path
import sys
import threading
import types
import wave
from unittest.mock import patch

from tests.base import TempDatabaseTest
from voice.devices import audio_level, friendly_audio_error, list_microphones, validate_microphone
from voice.audio_processing import AutomaticGain
from voice.manager import VoiceSessionManager
from voice.sapi_tts import SapiTTS
from voice.vosk_stt import VoskSTT


class VoiceV2Tests(TempDatabaseTest):
    def test_microphone_selection(self):
        fake = types.SimpleNamespace(query_devices=lambda: [
            {"name": "Saída", "max_input_channels": 0},
            {"name": "Microfone", "max_input_channels": 1, "default_samplerate": 16000},
        ])
        with patch.dict(sys.modules, {"sounddevice": fake}):
            self.assertEqual(list_microphones()[0]["id"], 1)
            self.assertEqual(validate_microphone(1), (True, "Microfone"))
            self.assertFalse(validate_microphone(9)[0])

    def test_sapi_prefers_female_portuguese(self):
        voices = [{"name": "English", "culture": "en-GB", "gender": "Female"}, {"name": "Maria", "culture": "pt-BR", "gender": "Female"}]
        with patch.object(SapiTTS, "list_voices", return_value=voices):
            self.assertEqual(SapiTTS.preferred_voice(), "Maria")

    def test_wav_fixture_transcription_contract(self):
        model = self.root / "model"; model.mkdir()
        wav_path = self.root / "silence.wav"
        with wave.open(str(wav_path), "wb") as audio:
            audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000); audio.writeframes(b"\0\0" * 400)

        class Recognizer:
            def __init__(self, *_): pass
            def AcceptWaveform(self, _): return True
            def FinalResult(self): return json.dumps({"text": "teste local"})

        vosk = types.SimpleNamespace(Model=lambda _: object(), KaldiRecognizer=Recognizer)
        sounddevice = types.SimpleNamespace()
        with patch.dict(sys.modules, {"vosk": vosk, "sounddevice": sounddevice}):
            self.assertEqual(VoskSTT(model).transcribe_wav(wav_path), "teste local")

    def test_friendly_microphone_diagnostics(self):
        self.assertIn("Privacidade", friendly_audio_error("Unanticipated host error -9999"))
        self.assertAlmostEqual(audio_level(b"\0\0" * 20), 0.0)

    def test_automatic_gain_amplifies_low_voice_without_amplifying_silence(self):
        processor = AutomaticGain(max_gain=12, enabled=True)
        silence, silence_info = processor.process(array("h", [0] * 100).tobytes())
        quiet, quiet_info = processor.process(array("h", [120] * 100).tobytes())
        self.assertEqual(audio_level(silence), 0.0)
        self.assertGreater(quiet_info.output_level, quiet_info.raw_level * 4)
        self.assertLessEqual(quiet_info.gain, 12)

    def test_voice_session_keeps_followup_context_until_timeout(self):
        class STT:
            _model = None
            def __init__(self): self.responses = iter(("primeira pergunta", "e depois", "")); self.unloads = 0
            def listen_once(self, timeout, on_level=None):
                if on_level: on_level(0.2)
                return next(self.responses)
            def unload(self): self.unloads += 1

        class TTS:
            def __init__(self): self.spoken = []
            def speak(self, text): self.spoken.append(text)

        stt, tts = STT(), TTS()
        manager = VoiceSessionManager(self.settings(tts_enabled=True, conversation_followup_seconds=8), stt=stt, tts=tts)
        first, followup, closed = threading.Event(), threading.Event(), threading.Event()
        heard = []
        manager.start_session(lambda text: (heard.append(text), first.set()), self.fail)
        self.assertTrue(first.wait(1))
        manager.respond_and_follow_up("resposta um", lambda text: (heard.append(text), followup.set()), self.fail, closed.set)
        self.assertTrue(followup.wait(1))
        self.assertTrue(manager.session.active)
        self.assertEqual(manager.session.turns, 2)
        manager.respond_and_follow_up("resposta dois", heard.append, self.fail, closed.set)
        self.assertTrue(closed.wait(1))
        self.assertFalse(manager.session.active)
        self.assertEqual(heard, ["primeira pergunta", "e depois"])
        self.assertEqual(tts.spoken, ["resposta um", "resposta dois"])
        self.assertEqual(stt.unloads, 1)
