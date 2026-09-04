from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

from config import Settings
from downloads.manager import DownloadManager, DownloadSpec
from voice.devices import default_input_device_id, friendly_audio_error, list_microphones
from voice.sapi_tts import SapiTTS
from voice.vosk_stt import VoskSTT


VOSK_PT = DownloadSpec(
    name="Vosk Portuguese/Brazilian Portuguese small 0.3",
    url="https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip",
    size_bytes=31 * 1024 * 1024,
    license="Apache-2.0",
    sha256=None,  # A página oficial não publica checksum; tamanho e ZIP são validados.
)


def safe_extract(archive: Path, target: Path) -> Path:
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            resolved = (target / member.filename).resolve()
            if target.resolve() not in resolved.parents and resolved != target.resolve(): raise ValueError("ZIP contém caminho inseguro.")
        bundle.extractall(target)
    models = [p for p in target.iterdir() if p.is_dir()]
    if not models: raise ValueError("Modelo não encontrado no ZIP.")
    return models[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Assistente de configuração de voz da Naty")
    parser.add_argument("--yes", action="store_true", help="confirma o download previamente informado")
    parser.add_argument("--skip-live-test", action="store_true")
    args = parser.parse_args(); settings = Settings.load()
    print(f"Modelo: {VOSK_PT.name}\nOrigem: {VOSK_PT.url}\nTamanho publicado: 31 MB\nLicença: {VOSK_PT.license}")
    print("Checksum: não publicado pela origem; o instalador valida HTTPS, tamanho e integridade do ZIP.")
    if not args.yes and input("Baixar e instalar este modelo? [s/N] ").strip().lower() not in {"s", "sim"}: return 1
    model_root = PROJECT_ROOT / "models" / "vosk"; archive = model_root / "vosk-model-small-pt-0.3.zip"
    if not (model_root / "vosk-model-small-pt-0.3").is_dir():
        DownloadManager().download(VOSK_PT, archive, lambda done, total: print(f"\r{done/1024/1024:.1f}/{total/1024/1024:.1f} MB", end="", flush=True))
        print(); model_path = safe_extract(archive, model_root); archive.unlink(missing_ok=True)
    else: model_path = model_root / "vosk-model-small-pt-0.3"
    microphones = list_microphones()
    if not microphones: print("Nenhum microfone encontrado. O modelo foi instalado, mas o teste ao vivo não pode continuar."); return 2
    print("Microfones:")
    for item in microphones:
        marker = " (padrão)" if item.get("is_default") else ""
        print(f"  [{item['id']}] {item['name']} · {item.get('hostapi', '')} · {item['default_samplerate']} Hz{marker}")
    os_default = default_input_device_id()
    default_id = os_default if any(item["id"] == os_default for item in microphones) else microphones[0]["id"]
    raw = input(f"Escolha o dispositivo [{default_id}]: ").strip() if not args.yes else ""
    device_id = int(raw) if raw else default_id
    if not any(item["id"] == device_id for item in microphones):
        print("Dispositivo inválido. Execute novamente e escolha um ID listado."); return 2
    settings.vosk_model_path, settings.microphone_device, settings.voice_enabled = str(model_path), device_id, True
    if not settings.voice: settings.voice = SapiTTS.preferred_voice()
    settings.save(); print(f"Configurado: {next(d['name'] for d in microphones if d['id'] == device_id)}")
    if args.skip_live_test: return 0
    print("Fale um comando curto em português (até 8 segundos)...")
    try: text = VoskSTT(str(model_path), device=device_id).listen_once(8)
    except Exception as exc:
        print(f"Falha no microfone: {friendly_audio_error(exc)}"); return 3
    print(f"Transcrição: {text or '[silêncio/incompreensível]'}")
    SapiTTS(settings.voice, settings.voice_rate, settings.voice_volume).speak("Teste concluído. Esta é a voz da Naty.")
    return 0 if text else 3


if __name__ == "__main__": raise SystemExit(main())
