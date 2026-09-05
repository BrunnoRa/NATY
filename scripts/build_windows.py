from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.0.0"
DIST = ROOT / "dist"
HYBRID = DIST / "NatyHybrid"


def run(*args: str) -> None:
    print("+", " ".join(args))
    subprocess.run(args, cwd=ROOT, check=True)


def find_iscc() -> Path | None:
    located = shutil.which("ISCC.exe")
    candidates = [
        Path(located) if located else None,
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ]
    return next((path for path in candidates if path and path.is_file()), None)


def dotnet() -> Path:
    bundled = ROOT / ".dotnet" / "dotnet.exe"
    if bundled.is_file():
        return bundled
    located = shutil.which("dotnet")
    if located:
        return Path(located)
    raise FileNotFoundError("SDK .NET 8 não encontrado.")


def portable_package(app_dir: Path) -> Path:
    output_dir = ROOT / "installer"
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"Naty-Windows-{VERSION}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for source in app_dir.rglob("*"):
            if source.is_file():
                archive.write(source, Path("NATY") / source.relative_to(app_dir))
    return zip_path


def main() -> int:
    run(sys.executable, "-m", "scripts.generate_assets")
    run(sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", "naty_core.spec")
    if HYBRID.exists():
        shutil.rmtree(HYBRID)
    run(str(dotnet()), "publish", "desktop/Naty.Desktop/Naty.Desktop.csproj", "-c", "Release",
        "-r", "win-x64", "--self-contained", "true", "-o", str(HYBRID),
        "--source", "https://api.nuget.org/v3/index.json")
    shutil.copytree(DIST / "Naty.Core", HYBRID / "Core")
    shutil.copy2(ROOT / "config.example.toml", HYBRID / "config.example.toml")
    expected = (HYBRID / "Naty.exe", HYBRID / "Core" / "Naty.Core.exe")
    missing = [str(path) for path in expected if not path.is_file()]
    if missing:
        raise FileNotFoundError("Artefatos híbridos ausentes: " + ", ".join(missing))
    archive = portable_package(HYBRID)
    print(f"Pacote portátil: {archive}")
    iscc = find_iscc()
    if iscc:
        run(str(iscc), str(ROOT / "packaging" / "Naty.iss"))
        print(f"Instalador: {ROOT / 'installer' / 'NatySetup.exe'}")
    else:
        print("Inno Setup não encontrado; o ZIP híbrido foi criado e NatySetup.exe não foi compilado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
