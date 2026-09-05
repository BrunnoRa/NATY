from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import Settings
from voice.whisper_setup import WHISPER_BASE, WHISPER_RUNTIME, diagnostics, install_whisper


def _describe(label, spec) -> None:
    print(f"{label}: {spec.name}")
    print(f"Origem: {spec.url}")
    print(f"Tamanho: {(spec.size_bytes or 0) / 1024 / 1024:.1f} MiB")
    print(f"Licença: {spec.license}")
    print(f"SHA-256: {spec.sha256}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Configura o Whisper Base multilingual oficial para a NATY")
    parser.add_argument("--yes", action="store_true", help="confirma os downloads descritos sem perguntar")
    parser.add_argument("--status", action="store_true", help="mostra apenas o diagnóstico atual")
    args = parser.parse_args()
    settings = Settings.load()
    current = diagnostics(settings.whisper_executable_path, settings.whisper_model_path)
    if args.status:
        print(current["status"])
        print(f"Arquitetura: {current['architecture']} · {'compatível' if current['architecture_ok'] else 'incompatível'}")
        print(f"Runtime: {current['runtime_path'] or 'não configurado'}")
        print(f"Modelo: {current['model_path'] or 'não configurado'}")
        return 0 if current["ready"] else 1
    _describe("Runtime", WHISPER_RUNTIME)
    _describe("Modelo", WHISPER_BASE)
    if not args.yes and input("Baixar e configurar estes arquivos? [s/N] ").strip().casefold() not in {"s", "sim"}:
        print("Configuração cancelada; nenhum download foi iniciado.")
        return 1
    try:
        result = install_whisper(settings, progress=lambda done, total: print(
            f"\rDownload: {done / 1024 / 1024:.1f}/{total / 1024 / 1024:.1f} MiB", end="", flush=True))
    except Exception as exc:
        print(f"\nFalha ao configurar Whisper: {exc}")
        return 2
    print(f"\n{result['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
