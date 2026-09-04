from __future__ import annotations
from pathlib import Path
import sys, time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import Settings
from voice.devices import list_microphones
from voice.vosk_stt import VoskSTT

settings = Settings.load(); devices = list_microphones(); started = time.perf_counter()
print("Microfone:", next((d["name"] for d in devices if d["id"] == settings.microphone_device), "padrão"))
text = VoskSTT(settings.vosk_model_path, device=settings.microphone_device).listen_once(8)
print("Duração/latência total:", round(time.perf_counter()-started, 2), "s")
print("Transcrição:", text)
raise SystemExit(0 if text else 1)
