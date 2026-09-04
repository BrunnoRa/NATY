from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def startup_command(app_path: str | None = None) -> str:
    """Monta o comando correto para código-fonte ou executável empacotado."""
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}"'
    target = Path(app_path or sys.argv[0]).resolve()
    interpreter = Path(sys.executable).resolve()
    pythonw = interpreter.with_name("pythonw.exe")
    if pythonw.is_file():
        interpreter = pythonw
    return f'"{interpreter}" "{target}"'


def set_start_with_windows(enabled: bool, app_path: str | None = None) -> bool:
    """Altera startup somente quando chamado por uma ação explícita do usuário."""
    if os.name != "nt": return False
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, "Naty", 0, winreg.REG_SZ, startup_command(app_path))
        else:
            try: winreg.DeleteValue(key, "Naty")
            except FileNotFoundError: pass
    return True


def open_path(path: Path) -> None:
    if os.name == "nt": os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin": subprocess.Popen(["open", str(path)])
    else: subprocess.Popen(["xdg-open", str(path)])
