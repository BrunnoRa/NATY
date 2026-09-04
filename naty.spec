# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, get_package_paths


project_root = Path(SPEC).resolve().parent
hiddenimports = (
    collect_submodules("pystray")
    + collect_submodules("ddgs")
    + collect_submodules("vosk")
    + collect_submodules("sounddevice")
)
asset_names = ("naty.ico", "naty_16.png", "naty_32.png", "naty_48.png", "naty_128.png", "naty_256.png")
datas = [(str(project_root / "assets" / name), "assets") for name in asset_names]
vosk_package = Path(get_package_paths("vosk")[1])
binaries = [(str(vosk_package / "libvosk.dll"), "vosk")]
vosk_model = project_root / "models" / "vosk" / "vosk-model-small-pt-0.3"
if vosk_model.is_dir():
    datas.append((str(vosk_model), "models/vosk/vosk-model-small-pt-0.3"))

a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["torch", "tensorflow"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Naty",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "assets" / "naty.ico"),
    version=str(project_root / "packaging" / "version_info.txt"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="Naty",
)
