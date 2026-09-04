from __future__ import annotations

import base64
import os
import subprocess

from voice.tts_base import TTSProvider


class SapiTTS(TTSProvider):
    def __init__(self, voice: str = "", rate: int = 0, volume: int = 100):
        self.voice, self.rate, self.volume = voice, max(-10, min(10, rate)), max(0, min(100, volume))

    def available(self) -> bool: return os.name == "nt"

    @staticmethod
    def list_voices() -> list[dict]:
        if os.name != "nt": return []
        import json
        script = "Add-Type -AssemblyName System.Speech;$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;$s.GetInstalledVoices()|%%{$_.VoiceInfo}|Select-Object Name,Culture,Gender|ConvertTo-Json -Compress;$s.Dispose()"
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script], capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=15, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode or not result.stdout.strip(): return []
        try:
            raw = json.loads(result.stdout); rows = raw if isinstance(raw, list) else [raw]
            return [{"name": r.get("Name", ""), "culture": r.get("Culture", ""), "gender": r.get("Gender", "")} for r in rows]
        except (ValueError, TypeError): return []

    @classmethod
    def preferred_voice(cls) -> str:
        voices = cls.list_voices()
        female = [v for v in voices if str(v.get("gender", "")).lower() == "female"]
        preferred = next((v for v in female if str(v.get("culture", "")).lower().startswith("pt")), None)
        preferred = preferred or next((v for v in female if "gb" in str(v.get("culture", "")).lower()), None)
        return str((preferred or (female[0] if female else voices[0] if voices else {})).get("name", ""))

    def speak(self, text: str) -> None:
        if not self.available() or not text.strip(): return
        encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        selected_voice = self.voice or self.preferred_voice()
        voice64 = base64.b64encode(selected_voice.encode("utf-8")).decode("ascii")
        script = (
            "Add-Type -AssemblyName System.Speech;"
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            f"$s.Rate={self.rate};$s.Volume={self.volume};"
            f"$v=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{voice64}'));"
            "if($v){try{$s.SelectVoice($v)}catch{}};"
            f"$t=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded}'));"
            "$s.Speak($t);$s.Dispose()"
        )
        subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                       check=False, timeout=max(15, len(text) // 8), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
