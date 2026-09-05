from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import zipfile

from config import Settings, user_data_root
from downloads.manager import DownloadManager, DownloadSpec
from voice.whisper_setup import file_sha256, is_windows_x64


PIPER_VERSION = "2023.11.14-2"
VOICE_REVISION = "1162a9173d0ce503555aed757976b7a9912eae4c"
PIPER_RUNTIME = DownloadSpec(
    name="Piper v1.2.0 Windows AMD64",
    url=f"https://github.com/rhasspy/piper/releases/download/{PIPER_VERSION}/piper_windows_amd64.zip",
    size_bytes=22_477_236,
    license="MIT",
    sha256=None,
)
PIPER_FABER = DownloadSpec(
    name="Piper Faber medium pt-BR",
    url=f"https://huggingface.co/rhasspy/piper-voices/resolve/{VOICE_REVISION}/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx",
    size_bytes=63_201_294,
    license="CC0 (dataset); repositório piper-voices MIT",
    sha256="858555e3a064209c57088fe6bd70c4c3dc54d03eaa00c45d5ecaf43a33f95aa7",
)
PIPER_FABER_CONFIG = DownloadSpec(
    name="Configuração Piper Faber medium pt-BR",
    url=f"https://huggingface.co/rhasspy/piper-voices/resolve/{VOICE_REVISION}/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json",
    size_bytes=4_855,
    license="CC0 (dataset); repositório piper-voices MIT",
    sha256="7e694de195ae3fc36dd732c445eb04fb49b649854893cb5506b978f0d50a1d6f",
)


def safe_extract_runtime(archive: str | Path, target: str | Path) -> Path:
    destination = Path(target).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            resolved = (destination / member.filename).resolve()
            if resolved != destination and destination not in resolved.parents:
                raise ValueError("ZIP do Piper contém caminho inseguro.")
        bundle.extractall(destination)
    executable = next(destination.rglob("piper.exe"), None)
    if executable is None:
        raise ValueError("piper.exe não foi encontrado no pacote oficial.")
    return executable


def diagnostics(executable: str | Path = "", model_path: str | Path = "", config_path: str | Path = "") -> dict:
    executable_path = Path(executable) if executable else None
    model = Path(model_path) if model_path else None
    config = Path(config_path) if config_path else None
    architecture_ok = is_windows_x64()
    parts = {
        "runtime_available": bool(executable_path and executable_path.is_file()),
        "model_available": bool(model and model.is_file()),
        "config_available": bool(config and config.is_file()),
    }
    ready = architecture_ok and all(parts.values())
    return {
        "ready": ready,
        "status": "Piper Faber pt-BR pronto." if ready else "Piper neural não instalado.",
        "architecture_ok": architecture_ok,
        "provider": "Piper Faber medium pt-BR",
        "executable_path": str(executable_path or ""),
        "model_path": str(model or ""),
        "config_path": str(config or ""),
        **parts,
    }


def install_piper(settings: Settings, root: str | Path | None = None, progress=None) -> dict:
    if not is_windows_x64():
        raise RuntimeError("Esta configuração do Piper requer Windows x64.")
    install_root = Path(root) if root else user_data_root() / "models" / "piper"
    runtime_root = install_root / f"runtime-{PIPER_VERSION}"
    archive = install_root / f"piper-windows-amd64-{PIPER_VERSION}.zip"
    voice_root = install_root / "voices" / "pt_BR-faber-medium"
    model = voice_root / "pt_BR-faber-medium.onnx"
    config = voice_root / "pt_BR-faber-medium.onnx.json"
    manager = DownloadManager()
    executable = next(runtime_root.rglob("piper.exe"), None) if runtime_root.exists() else None
    runtime_sha256 = ""
    if executable is None:
        manager.download(PIPER_RUNTIME, archive, progress)
        runtime_sha256 = file_sha256(archive)
        executable = safe_extract_runtime(archive, runtime_root)
        archive.unlink(missing_ok=True)
    if not model.is_file() or file_sha256(model) != PIPER_FABER.sha256:
        manager.download(PIPER_FABER, model, progress)
    if not config.is_file() or file_sha256(config) != PIPER_FABER_CONFIG.sha256:
        manager.download(PIPER_FABER_CONFIG, config, progress)
    settings.piper_executable_path = str(executable)
    settings.piper_model_path = str(model)
    settings.piper_config_path = str(config)
    settings.tts_provider = "piper"
    settings.save()
    manifest = {
        "runtime": {**asdict(PIPER_RUNTIME), "installed_sha256": runtime_sha256 or None},
        "voice": asdict(PIPER_FABER), "config": asdict(PIPER_FABER_CONFIG),
        "version": PIPER_VERSION, "voice_revision": VOICE_REVISION,
        "architecture": "windows-x64",
        "installed": {"executable": str(executable), "model": str(model), "config": str(config)},
    }
    install_root.mkdir(parents=True, exist_ok=True)
    (install_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return diagnostics(executable, model, config)
