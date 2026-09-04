from __future__ import annotations

import base64
import locale
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
        script = (
            "[Console]::OutputEncoding=[Text.UTF8Encoding]::new();"
            "$s=New-Object -ComObject SAPI.SpVoice;$voices=$s.GetVoices();$rows=@();"
            "for($i=0;$i -lt $voices.Count;$i++){$v=$voices.Item($i);"
            "$rows += [PSCustomObject]@{Name=$v.GetDescription();Culture=$v.GetAttribute('Language');Gender=$v.GetAttribute('Gender')}};"
            "$rows|ConvertTo-Json -Compress"
        )
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script], capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=15, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode or not result.stdout.strip(): return []
        try:
            raw = json.loads(result.stdout); rows = raw if isinstance(raw, list) else [raw]
            voices = []
            for row in rows:
                culture = str(row.get("Culture", ""))
                try:
                    language = locale.windows_locale.get(int(culture.split(";", 1)[0], 16), culture).replace("_", "-")
                except ValueError:
                    language = culture
                voices.append({"name": row.get("Name", ""), "culture": language, "gender": row.get("Gender", "")})
            return voices
        except (ValueError, TypeError): return []

    @classmethod
    def preferred_voice(cls) -> str:
        voices = cls.list_voices()
        female = [v for v in voices if str(v.get("gender", "")).lower() == "female"]
        preferred = next((v for v in female if str(v.get("culture", "")).lower().startswith("pt")), None)
        preferred = preferred or next((v for v in female if "gb" in str(v.get("culture", "")).lower()), None)
        return str((preferred or (female[0] if female else voices[0] if voices else {})).get("name", ""))

    @classmethod
    def has_female_pt_br(cls) -> bool:
        return any(str(v.get("gender", "")).casefold() == "female" and str(v.get("culture", "")).casefold().startswith("pt-br")
                   for v in cls.list_voices())

    @staticmethod
    def windows_voice_setup_instructions() -> str:
        return ("Abra Configurações do Windows > Hora e idioma > Fala > Gerenciar vozes > Adicionar vozes, "
                "instale Português (Brasil) e reinicie a Naty. As vozes do Windows são gratuitas.")

    def speak(self, text: str) -> None:
        if not self.available() or not text.strip(): return
        encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        selected_voice = self.voice or self.preferred_voice()
        voice64 = base64.b64encode(selected_voice.encode("utf-8")).decode("ascii")
        script = (
            "$s=New-Object -ComObject SAPI.SpVoice;"
            f"$s.Rate={self.rate};$s.Volume={self.volume};"
            f"$v=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{voice64}'));"
            "if($v){$voices=$s.GetVoices();for($i=0;$i -lt $voices.Count;$i++){"
            "if($voices.Item($i).GetDescription() -eq $v){$s.Voice=$voices.Item($i);break}}};"
            f"$t=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded}'));"
            "[void]$s.Speak($t)"
        )
        subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                       check=False, timeout=max(15, len(text) // 8), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
