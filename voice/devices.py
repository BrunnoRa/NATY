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


def _device_key(value: object) -> str:
    return " ".join(str(value or "").casefold().split())


def resolve_microphone(
    device_id: int = -1,
    name: str = "",
    hostapi: str = "",
    sample_rate: int = 0,
) -> dict | None:
    """Resolve um microfone por identidade estável após o Windows renumerar IDs."""
    devices = list_microphones()
    if not devices:
        return None

    stored = next((device for device in devices if device["id"] == device_id), None)
    wanted_name, wanted_host = _device_key(name), _device_key(hostapi)
    if wanted_name:
        candidates = [device for device in devices if _device_key(device.get("name")) == wanted_name]
        if wanted_host:
            same_host = [device for device in candidates if _device_key(device.get("hostapi")) == wanted_host]
            if same_host:
                candidates = same_host
        if sample_rate:
            same_rate = [device for device in candidates if int(device.get("default_samplerate", 0)) == int(sample_rate)]
            if same_rate:
                candidates = same_rate
        if stored in candidates:
            return dict(stored)
        if candidates:
            return dict(next((device for device in candidates if device.get("is_default")), candidates[0]))

    if stored:
        return dict(stored)
    return dict(next((device for device in devices if device.get("is_default")), devices[0]))


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
        return "O reconhecimento de voz não está configurado. Abra Configurações > Voz para concluir a instalação."
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
    started = time.perf_counter()
    try:
        selected = device_id if device_id >= 0 else None
        native_rate = int(sd.query_devices(selected, "input").get("default_samplerate", sample_rate))
    except Exception:
        native_rate = sample_rate
    last_error = None
    for rate in dict.fromkeys((sample_rate, native_rate)):
        levels: list[float] = []
        def callback(indata, frames, time_info, status):
            level = audio_level(bytes(indata)); levels.append(level)
            if on_level: on_level(level)
        kwargs = {"samplerate": rate, "blocksize": max(800, rate // 10), "dtype": "int16", "channels": 1, "callback": callback}
        if device_id >= 0: kwargs["device"] = device_id
        try:
            with sd.RawInputStream(**kwargs): sd.sleep(max(1, int(duration * 1000)))
            return {"ok": True, "peak": max(levels or [0.0]), "sample_rate": rate,
                    "latency_ms": (time.perf_counter() - started) * 1000, "reason": "Áudio capturado."}
        except Exception as exc:
            last_error = exc
    return {"ok": False, "peak": 0.0, "sample_rate": native_rate,
            "latency_ms": (time.perf_counter() - started) * 1000, "reason": friendly_audio_error(last_error or "erro desconhecido")}
