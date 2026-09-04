import json
from pathlib import Path
import sys
import types
import wave
from unittest.mock import patch

from tests.base import TempDatabaseTest
from voice.devices import list_microphones, validate_microphone
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
