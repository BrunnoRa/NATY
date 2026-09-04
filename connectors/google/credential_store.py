from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import subprocess
from pathlib import Path


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


class DpapiCredentialStore:
    """Encrypts OAuth material for the current Windows user with DPAPI."""

    CRYPTPROTECT_UI_FORBIDDEN = 0x01

    def __init__(self, path: str | Path):
        self.path = Path(path)

    @staticmethod
    def _blob(data: bytes) -> tuple[_DataBlob, ctypes.Array]:
        buffer = ctypes.create_string_buffer(data)
        blob = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
        return blob, buffer

    def save(self, value: str) -> None:
        if not hasattr(ctypes, "windll"):
            raise RuntimeError("O cofre DPAPI só está disponível no Windows.")
        raw = value.encode("utf-8")
        source, source_buffer = self._blob(raw)
        protected = _DataBlob()
        protect = ctypes.windll.crypt32.CryptProtectData
        protect.argtypes = [
            ctypes.POINTER(_DataBlob), wintypes.LPCWSTR, ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
            ctypes.POINTER(_DataBlob),
        ]
        protect.restype = wintypes.BOOL
        ok = protect(
            ctypes.byref(source), "Naty Google OAuth", None, None, None,
            self.CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(protected),
        )
        _ = source_buffer
        if not ok:
            self._save_with_powershell(value)
            return
        try:
            encrypted = ctypes.string_at(protected.pbData, protected.cbData)
        finally:
            self._local_free(protected.pbData)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(base64.b64encode(encrypted))

    def load(self) -> str | None:
        if not self.path.is_file():
            return None
        if not hasattr(ctypes, "windll"):
            raise RuntimeError("O cofre DPAPI só está disponível no Windows.")
        stored = self.path.read_bytes()
        if stored.startswith(b"ps-dpapi:"):
            return self._load_with_powershell(stored.removeprefix(b"ps-dpapi:").decode("ascii"))
        encrypted = base64.b64decode(stored, validate=True)
        source, source_buffer = self._blob(encrypted)
        plain = _DataBlob()
        unprotect = ctypes.windll.crypt32.CryptUnprotectData
        unprotect.argtypes = [
            ctypes.POINTER(_DataBlob), ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
            ctypes.POINTER(_DataBlob),
        ]
        unprotect.restype = wintypes.BOOL
        ok = unprotect(
            ctypes.byref(source), None, None, None, None,
            self.CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(plain),
        )
        _ = source_buffer
        if not ok:
            raise ctypes.WinError()
        try:
            return ctypes.string_at(plain.pbData, plain.cbData).decode("utf-8")
        finally:
            self._local_free(plain.pbData)

    @staticmethod
    def _local_free(pointer) -> None:
        local_free = ctypes.windll.kernel32.LocalFree
        local_free.argtypes = [ctypes.c_void_p]
        local_free.restype = ctypes.c_void_p
        local_free(pointer)

    def _save_with_powershell(self, value: str) -> None:
        script = "$i=[Console]::In.ReadToEnd();$p=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($i));$s=ConvertTo-SecureString $p -AsPlainText -Force;$s|ConvertFrom-SecureString"
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            input=base64.b64encode(value.encode("utf-8")), capture_output=True,
            timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode or not result.stdout.strip():
            raise RuntimeError("O Windows não conseguiu proteger o token OAuth com DPAPI.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(b"ps-dpapi:" + result.stdout.strip())

    @staticmethod
    def _load_with_powershell(encrypted: str) -> str:
        script = "$e=[Console]::In.ReadToEnd();$s=ConvertTo-SecureString $e;$b=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($s);try{$p=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($b);[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($p))}finally{[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b)}"
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            input=encrypted.encode("ascii"), capture_output=True,
            timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode:
            raise RuntimeError("O Windows não conseguiu abrir o token OAuth protegido.")
        return base64.b64decode(result.stdout.strip(), validate=True).decode("utf-8")

    def clear(self) -> bool:
        if not self.path.exists():
            return False
        self.path.unlink()
        return True
