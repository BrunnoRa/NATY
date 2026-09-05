from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import Settings
from voice.piper_setup import PIPER_FABER, PIPER_FABER_CONFIG, PIPER_RUNTIME, diagnostics, install_piper


def _describe(spec) -> None:
    print(f"Artefato: {spec.name}\nOrigem: {spec.url}\nTamanho: {(spec.size_bytes or 0) / 1024 / 1024:.1f} MiB")
    print(f"Licença: {spec.license}\nSHA-256: {spec.sha256 or 'não publicado pela origem (ZIP e tamanho serão validados)'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Configura a voz neural pt-BR da NATY")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args(); settings = Settings.load()
    status = diagnostics(settings.piper_executable_path, settings.piper_model_path, settings.piper_config_path)
    if args.status:
        print(status["status"])
        return 0 if status["ready"] else 1
    for spec in (PIPER_RUNTIME, PIPER_FABER, PIPER_FABER_CONFIG): _describe(spec)
    if not args.yes and input("Baixar e configurar a voz neural? [s/N] ").strip().casefold() not in {"s", "sim"}:
        print("Configuração cancelada; nenhum download foi iniciado."); return 1
    try:
        result = install_piper(settings, progress=lambda done, total: print(
            f"\rDownload: {done / 1024 / 1024:.1f}/{total / 1024 / 1024:.1f} MiB", end="", flush=True))
    except Exception as exc:
        print(f"\nFalha ao configurar Piper: {exc}"); return 2
    print(f"\n{result['status']}"); return 0


if __name__ == "__main__": raise SystemExit(main())
