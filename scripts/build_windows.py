from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
VERSION = "2.1.0"


def run(*args: str) -> None:
    print("+", " ".join(args))
    subprocess.run(args, cwd=ROOT, check=True)


def find_iscc() -> Path | None:
    located = shutil.which("ISCC.exe")
    candidates = [
        Path(located) if located else None,
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ]
    return next((path for path in candidates if path and path.is_file()), None)


def portable_package(app_dir: Path) -> Path:
    output_dir = ROOT / "installer"
    stage = output_dir / f"Naty-Windows-{VERSION}"
    if stage.exists():
        shutil.rmtree(stage)
    shutil.copytree(app_dir, stage / "Naty")
    for name in ("install_naty.ps1", "uninstall_naty.ps1", "Instalar Naty.cmd"):
        shutil.copy2(ROOT / "packaging" / name, stage / name)
    (stage / "LEIA-ME.txt").write_text(
        "NATY 2.1\n\nExecute 'Instalar Naty.cmd'.\n"
        "A instalação é feita apenas para o usuário atual e cria atalhos no Desktop e menu Iniciar.\n",
        encoding="utf-8",
    )
    zip_path = output_dir / f"Naty-Windows-{VERSION}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for source in stage.rglob("*"):
            if source.is_file():
                archive.write(source, source.relative_to(stage.parent))
    return zip_path


def main() -> int:
    run(sys.executable, "-m", "scripts.generate_assets")
    run(sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", "naty.spec")
    app_dir = ROOT / "dist" / "Naty"
    executable = app_dir / "Naty.exe"
    if not executable.is_file():
        raise FileNotFoundError(executable)
    archive = portable_package(app_dir)
    print(f"Pacote portátil: {archive}")
    iscc = find_iscc()
    if iscc:
        run(str(iscc), str(ROOT / "packaging" / "Naty.iss"))
    else:
        print("Inno Setup não encontrado; o ZIP instalável foi criado normalmente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
