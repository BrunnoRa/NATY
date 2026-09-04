from __future__ import annotations


def list_microphones() -> list[dict]:
    try: import sounddevice as sd
    except ImportError: return []
    result = []
    for index, device in enumerate(sd.query_devices()):
        if int(device.get("max_input_channels", 0)) > 0:
            result.append({"id": index, "name": str(device.get("name", f"Microfone {index}")),
                           "channels": int(device["max_input_channels"]),
                           "default_samplerate": int(device.get("default_samplerate", 16000))})
    return result


def validate_microphone(device_id: int) -> tuple[bool, str]:
    devices = list_microphones()
    if not devices: return False, "Nenhum microfone de entrada foi encontrado."
    if device_id < 0: return True, devices[0]["name"]
    found = next((d for d in devices if d["id"] == device_id), None)
    return (True, found["name"]) if found else (False, "O microfone configurado não está disponível.")
