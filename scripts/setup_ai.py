from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

from config import Settings
from downloads.manager import DownloadManager, DownloadSpec


QWEN_SMALL = DownloadSpec(
    name="Qwen3 0.6B Instruct Q4_K_M",
    url="https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q4_K_M.gguf",
    size_bytes=484_000_000,
    license="Apache-2.0",
    sha256=None,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Instalação opcional da IA local da Naty")
    parser.add_argument("--yes", action="store_true", help="confirma o download previamente informado")
    args = parser.parse_args()
    print(f"Modelo: {QWEN_SMALL.name}\nOrigem: {QWEN_SMALL.url}\nTamanho aproximado: 484 MB\nLicença: {QWEN_SMALL.license}")
    print("Uso: CPU somente, carregamento sob demanda e descarregamento após inatividade. Não usa GPU.")
    print("Checksum: não fixado neste projeto; o gerenciador valida HTTPS, origem e tamanho mínimo.")
    if not args.yes and input("Baixar este modelo opcional? [s/N] ").strip().casefold() not in {"s", "sim"}:
        return 1
    destination = PROJECT_ROOT / "models" / "llm" / "Qwen3-0.6B-Q4_K_M.gguf"
    if not destination.is_file():
        DownloadManager().download(
            QWEN_SMALL, destination,
            lambda done, total: print(f"\r{done / 1024**2:.1f}/{total / 1024**2:.1f} MiB", end="", flush=True),
        )
        print()
    settings = Settings.load()
    settings.ai_model_path = str(destination)
    try:
        import llama_cpp  # noqa: F401
        settings.ai_enabled = True
        status = "ativada"
    except ImportError:
        settings.ai_enabled = False
        status = "baixada, mas desativada até instalar requirements-local-ai.txt"
    settings.save()
    print(f"IA local {status}. Execute scripts/benchmark_llm.py para medir nesta máquina.")
    return 0


if __name__ == "__main__": raise SystemExit(main())
