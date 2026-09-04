from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import Settings
from voice.devices import default_input_device_id, friendly_audio_error, list_microphones, measure_microphone_level
from voice.sapi_tts import SapiTTS
from voice.vosk_stt import VoskSTT


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnóstico reproduzível de voz da Naty")
    parser.add_argument("--listen", action="store_true", help="faz contagem regressiva e transcreve até 7 segundos")
    parser.add_argument("--speak", action="store_true", help="reproduz uma frase pela voz SAPI selecionada")
    args = parser.parse_args()
    settings = Settings.load()
    devices = list_microphones()
    voices = SapiTTS.list_voices()
    selected = next((device for device in devices if device["id"] == settings.microphone_device), None)

    print(f"Dispositivo padrão: {default_input_device_id()}")
    for device in devices:
        marker = "*" if device["id"] == settings.microphone_device else " "
        print(f"{marker} [{device['id']}] {device['name']} · {device['hostapi']} · "
              f"{device['channels']} canal(is) · {device['default_samplerate']} Hz")
    print(f"Selecionado: {selected['name'] if selected else 'indisponível'}")
    print(f"Vosk instalado/modelo: {VoskSTT(settings.vosk_model_path).available()} · {settings.vosk_model_path}")
    print(f"Ganho: {'automático' if settings.automatic_gain_enabled else 'fixo'} · máximo {settings.microphone_gain:.1f}x")
    print("Vozes SAPI:")
    for voice in voices:
        print(f"  {voice['name']} · {voice['culture']} · {voice['gender']}")

    if not selected:
        print("FAIL: o microfone configurado não está na lista.")
        return 1
    level = measure_microphone_level(selected["id"], duration=1.0)
    print(f"Nível: {'OK' if level['ok'] else 'FAIL'} · pico {level['peak'] * 100:.2f}% · {level['reason']}")
    if not level["ok"]:
        return 1

    if args.listen:
        for remaining in (2, 1):
            print(f"Começando em {remaining}…", flush=True); time.sleep(1)
        print("Fale agora por até 7 segundos…", flush=True)
        levels: list[float] = []
        started = time.perf_counter()
        try:
            stt = VoskSTT(settings.vosk_model_path, device=selected["id"], microphone_gain=settings.microphone_gain,
                          automatic_gain=settings.automatic_gain_enabled)
            text = stt.listen_once(7, levels.append)
        except Exception as exc:
            print("FAIL:", friendly_audio_error(exc))
            return 1
        latency = (time.perf_counter() - started) * 1000
        print(f"Transcrição: {text or '(nenhuma fala reconhecida)'}")
        print(f"Latência: {latency:.0f} ms · pico {max(levels or [0]) * 100:.2f}%")
        print(f"Ganho aplicado no último bloco: {stt.last_gain:.1f}x · entrada {stt.last_raw_level * 100:.3f}% · processado {stt.last_output_level * 100:.3f}%")
        if not text:
            return 1

    if args.speak:
        SapiTTS(settings.voice, settings.voice_rate, settings.voice_volume).speak("Teste concluído. Esta é a voz da Naty.")
        print("TTS: frase enviada à voz SAPI selecionada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
