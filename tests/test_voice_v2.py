import json
from array import array
from pathlib import Path
import sys
import threading
import types
import wave
import zipfile
from unittest.mock import patch

from tests.base import TempDatabaseTest
from voice.devices import audio_level, friendly_audio_error, list_microphones, resolve_microphone, validate_microphone
from voice.audio_processing import AutomaticGain
from voice.manager import VoiceSessionManager
from voice.piper_tts import PiperTTS
from voice.piper_setup import diagnostics as piper_diagnostics, safe_extract_runtime as safe_extract_piper
from voice.sapi_tts import SapiTTS
from voice.vosk_stt import VoskSTT
from voice.whisper_setup import diagnostics as whisper_diagnostics, is_windows_x64, safe_extract_runtime


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

    def test_microphone_is_resolved_after_windows_reindexes_devices(self):
        devices = [
            {"id": 3, "name": "Microfone USB", "hostapi": "MME", "default_samplerate": 44100, "is_default": False},
            {"id": 19, "name": "Microfone Realtek", "hostapi": "Windows WDM-KS", "default_samplerate": 48000, "is_default": True},
        ]
        with patch("voice.devices.list_microphones", return_value=devices):
            resolved = resolve_microphone(13, "Microfone Realtek", "Windows WDM-KS", 48000)
        self.assertEqual(resolved["id"], 19)

    def test_microphone_resolution_falls_back_to_default(self):
        devices = [
            {"id": 4, "name": "USB", "hostapi": "MME", "default_samplerate": 44100, "is_default": False},
            {"id": 7, "name": "Padrão", "hostapi": "WASAPI", "default_samplerate": 48000, "is_default": True},
        ]
        with patch("voice.devices.list_microphones", return_value=devices):
            resolved = resolve_microphone(99, "Desconectado", "MME", 16000)
        self.assertEqual(resolved["id"], 7)

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

    def test_whisper_diagnostics_reports_missing_setup(self):
        result = whisper_diagnostics(self.root / "missing.exe", self.root / "missing.bin")
        self.assertFalse(result["ready"])
        self.assertIn("Whisper não instalado", result["status"])
        self.assertEqual(result["provider"], "Whisper Base multilingual")

    def test_whisper_runtime_extract_rejects_path_traversal(self):
        archive = self.root / "runtime.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("../escape.exe", b"bad")
        with self.assertRaisesRegex(ValueError, "inseguro"):
            safe_extract_runtime(archive, self.root / "runtime")

    def test_windows_x64_validation(self):
        self.assertTrue(is_windows_x64("AMD64", "Windows"))
        self.assertFalse(is_windows_x64("ARM64", "Windows"))

    def test_piper_diagnostics_requires_runtime_model_and_config(self):
        executable = self.root / "piper.exe"; executable.write_bytes(b"exe")
        model = self.root / "voice.onnx"; model.write_bytes(b"model")
        config = self.root / "voice.onnx.json"; config.write_text("{}")
        with patch("voice.piper_setup.is_windows_x64", return_value=True):
            self.assertTrue(piper_diagnostics(executable, model, config)["ready"])
            self.assertFalse(piper_diagnostics(executable, model, self.root / "missing.json")["ready"])

    def test_piper_runtime_extract_rejects_path_traversal(self):
        archive = self.root / "piper.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("../piper.exe", b"bad")
        with self.assertRaisesRegex(ValueError, "inseguro"):
            safe_extract_piper(archive, self.root / "piper")

    def test_piper_synthesizes_with_explicit_config(self):
        executable = self.root / "piper.exe"; executable.write_bytes(b"exe")
        model = self.root / "voice.onnx"; model.write_bytes(b"model")
        config = self.root / "voice.onnx.json"; config.write_text("{}")
        output = self.root / "voice.wav"

        class Process:
            returncode = 0
            def __init__(self, command, **_):
                target = Path(command[command.index("--output_file") + 1])
                with wave.open(str(target), "wb") as audio:
                    audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(22050); audio.writeframes(b"\0\0" * 100)
            def communicate(self, text, timeout): return "", ""

        with patch("voice.piper_tts.subprocess.Popen", side_effect=lambda command, **kwargs: Process(command, **kwargs)):
            result = PiperTTS(str(executable), str(model), str(config)).synthesize("Olá", output)
        self.assertEqual(result, output)
        self.assertGreater(output.stat().st_size, 44)

    def test_response_is_queued_by_complete_sentence(self):
        class TTS:
            def __init__(self): self.spoken = []
            def speak(self, text): self.spoken.append(text)
        tts = TTS()
        manager = VoiceSessionManager(self.settings(tts_enabled=True, tts_provider="sapi"), stt=object(), tts=tts)
        manager._speak_response("Primeira frase. Segunda! Terceira?")
        self.assertEqual(tts.spoken, ["Primeira frase.", "Segunda!", "Terceira?"])

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
