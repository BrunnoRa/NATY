from __future__ import annotations

from array import array
from collections.abc import Callable
import math
import time


def default_input_device_id() -> int:
    try:
        import sounddevice as sd
        value = sd.default.device
        try: device_id = value[0]
        except (TypeError, IndexError): device_id = int(value)
        return int(device_id)
    except (ImportError, TypeError, ValueError, AttributeError):
        return -1


def list_microphones() -> list[dict]:
    try: import sounddevice as sd
    except ImportError: return []
    default_id = default_input_device_id()
    try: hostapis = sd.query_hostapis()
    except Exception: hostapis = ()
    result = []
    for index, device in enumerate(sd.query_devices()):
        if int(device.get("max_input_channels", 0)) > 0:
            host_index = int(device.get("hostapi", -1))
            host_name = hostapis[host_index].get("name", "") if 0 <= host_index < len(hostapis) else ""
            result.append({"id": index, "name": str(device.get("name", f"Microfone {index}")),
                           "channels": int(device["max_input_channels"]),
                           "default_samplerate": int(device.get("default_samplerate", 16000)),
                           "hostapi": str(host_name), "is_default": index == default_id})
    return result


def validate_microphone(device_id: int) -> tuple[bool, str]:
    devices = list_microphones()
    if not devices: return False, "Nenhum microfone de entrada foi encontrado."
    if device_id < 0: return True, devices[0]["name"]
    found = next((d for d in devices if d["id"] == device_id), None)
    return (True, found["name"]) if found else (False, "O microfone configurado não está disponível.")


def friendly_audio_error(error: BaseException | str) -> str:
    text = str(error)
    lowered = text.casefold()
    if "já está ouvindo" in lowered:
        return text
    if "vosk" in lowered or "modelo pt-br" in lowered:
        return "O Vosk ou o modelo pt-BR não está disponível. Execute setup_voice.bat e confira o caminho do modelo."
    if "-9999" in lowered or "host error" in lowered or "directsound error" in lowered:
        return ("O Windows recusou a abertura do microfone. Verifique Configurações > Privacidade e segurança > "
                "Microfone, feche apps que possam estar usando o dispositivo e teste outra entrada da lista.")
    if "invalid sample rate" in lowered or "-9997" in lowered:
        return "A taxa de amostragem não é aceita por este dispositivo. Selecione outra entrada ou ajuste o formato no Windows."
    if "device unavailable" in lowered or "invalid device" in lowered or "-9996" in lowered:
        return "O microfone selecionado não está disponível. Reconecte-o ou escolha outro dispositivo."
    if "permission" in lowered or "access" in lowered:
        return "O acesso ao microfone foi negado. Autorize aplicativos de desktop nas configurações de privacidade do Windows."
    if "overflow" in lowered:
        return "O áudio chegou com interrupções. Feche aplicativos de áudio e tente novamente."
    return f"Não foi possível capturar o microfone: {text or 'motivo não informado pelo driver.'}"


def audio_level(samples: bytes) -> float:
    values = array("h")
    values.frombytes(samples)
    if not values:
        return 0.0
    rms = math.sqrt(sum(value * value for value in values) / len(values))
    return min(1.0, rms / 32768.0)


def measure_microphone_level(
    device_id: int,
    duration: float = 1.0,
    sample_rate: int = 16000,
    on_level: Callable[[float], None] | None = None,
) -> dict:
    try:
        import sounddevice as sd
    except ImportError:
        return {"ok": False, "peak": 0.0, "reason": "O pacote sounddevice não está instalado."}
    levels: list[float] = []

    def callback(indata, frames, time_info, status):
        level = audio_level(bytes(indata)); levels.append(level)
        if on_level: on_level(level)

    kwargs = {"samplerate": sample_rate, "blocksize": 1600, "dtype": "int16", "channels": 1, "callback": callback}
    if device_id >= 0: kwargs["device"] = device_id
    started = time.perf_counter()
    try:
        with sd.RawInputStream(**kwargs):
            sd.sleep(max(1, int(duration * 1000)))
    except Exception as exc:
        return {"ok": False, "peak": max(levels or [0.0]), "latency_ms": (time.perf_counter() - started) * 1000,
                "reason": friendly_audio_error(exc)}
    return {"ok": True, "peak": max(levels or [0.0]), "latency_ms": (time.perf_counter() - started) * 1000,
            "reason": "Áudio capturado."}
