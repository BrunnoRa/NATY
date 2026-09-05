from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import zipfile

from config import Settings, user_data_root
from downloads.manager import DownloadManager, DownloadSpec


WHISPER_RUNTIME = DownloadSpec(
    name="whisper.cpp Windows x64 CPU",
    url="https://github.com/ggml-org/whisper.cpp/releases/download/v1.9.0/whisper-bin-x64.zip",
    size_bytes=5_410_599,
    license="MIT",
    sha256="00c4304b6be363a224a4b69829df49009f74131df8c3ce6a5878b89a11cd26ef",
)
WHISPER_BASE = DownloadSpec(
    name="Whisper Base multilingual (GGML)",
    url="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
    size_bytes=147_951_465,
    license="MIT",
    sha256="60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe",
)
WHISPER_VERSION = "1.9.0"


def is_windows_x64(machine: str | None = None, system: str | None = None) -> bool:
    actual_machine = (machine or platform.machine()).casefold()
    actual_system = (system or platform.system()).casefold()
    return actual_system == "windows" and actual_machine in {"amd64", "x86_64"}


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_extract_runtime(archive: str | Path, target: str | Path) -> Path:
    destination = Path(target).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            resolved = (destination / member.filename).resolve()
            if resolved != destination and destination not in resolved.parents:
                raise ValueError("ZIP do whisper.cpp contém caminho inseguro.")
        bundle.extractall(destination)
    executable = next(destination.rglob("whisper-cli.exe"), None)
    if executable is None:
        raise ValueError("whisper-cli.exe não foi encontrado no pacote oficial.")
    return executable


def diagnostics(executable: str | Path = "", model_path: str | Path = "") -> dict:
    executable_path = Path(executable) if executable else None
    model = Path(model_path) if model_path else None
    architecture_ok = is_windows_x64()
    runtime_available = bool(executable_path and executable_path.is_file())
    model_available = bool(model and model.is_file())
    ready = architecture_ok and runtime_available and model_available
    if not architecture_ok:
        status = "O instalador oficial configurado exige Windows x64."
    elif not runtime_available or not model_available:
        missing = "runtime e modelo" if not runtime_available and not model_available else ("runtime" if not runtime_available else "modelo")
        status = f"Whisper não instalado: falta {missing}."
    else:
        status = "Whisper Base pronto."
    return {
        "ready": ready,
        "status": status,
        "architecture": f"{platform.system()} {platform.machine()}",
        "architecture_ok": architecture_ok,
        "runtime_available": runtime_available,
        "model_available": model_available,
        "runtime_path": str(executable_path or ""),
        "model_path": str(model or ""),
        "provider": "Whisper Base multilingual",
        "version": WHISPER_VERSION,
        "source": {"runtime": WHISPER_RUNTIME.url, "model": WHISPER_BASE.url},
        "license": {"runtime": WHISPER_RUNTIME.license, "model": WHISPER_BASE.license},
    }


def install_whisper(settings: Settings, root: str | Path | None = None, progress=None) -> dict:
    if not is_windows_x64():
        raise RuntimeError("Esta configuração do whisper.cpp requer Windows x64.")
    install_root = Path(root) if root else user_data_root() / "models" / "whisper"
    runtime_root = install_root / f"runtime-{WHISPER_VERSION}"
    model_root = install_root / "models"
    runtime_archive = install_root / f"whisper-bin-x64-{WHISPER_VERSION}.zip"
    model_path = model_root / "ggml-base.bin"
    manager = DownloadManager()

    executable = next(runtime_root.rglob("whisper-cli.exe"), None) if runtime_root.exists() else None
    if executable is None:
        manager.download(WHISPER_RUNTIME, runtime_archive, progress)
        executable = safe_extract_runtime(runtime_archive, runtime_root)
        runtime_archive.unlink(missing_ok=True)
    if not model_path.is_file() or file_sha256(model_path) != WHISPER_BASE.sha256:
        manager.download(WHISPER_BASE, model_path, progress)

    settings.whisper_executable_path = str(executable)
    settings.whisper_model_path = str(model_path)
    settings.stt_provider = "whisper_cpp"
    settings.save()
    manifest = {
        "runtime": asdict(WHISPER_RUNTIME),
        "model": asdict(WHISPER_BASE),
        "version": WHISPER_VERSION,
        "architecture": "windows-x64",
        "installed": {"executable": str(executable), "model": str(model_path)},
    }
    (install_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return diagnostics(executable, model_path)
