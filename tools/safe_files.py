from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
from typing import Callable

from core.models import ToolResult


class SafeFileAssistant:
    MAX_SCANNED = 5000
    MAX_RESULTS = 30
    MAX_DEPTH = 5

    def __init__(self, configured_roots: str = "", opener: Callable[[str], None] | None = None,
                 recycler: Callable[[Path], None] | None = None, context=None, project_root: Path | None = None):
        candidates = [Path(os.path.expandvars(item.strip())).expanduser() for item in configured_roots.split(";") if item.strip()]
        if not candidates:
            candidates = [Path.home() / "Documents", Path.home() / "Downloads", Path.home() / "Desktop"]
            if project_root: candidates.append(project_root)
        self.roots = tuple(dict.fromkeys(path.resolve() for path in candidates if path.exists()))
        self.opener = opener or self._open
        self.recycler = recycler or self._recycle
        self.context = context

    def _allowed(self, path: Path) -> bool:
        resolved = path.resolve()
        return any(resolved == root or root in resolved.parents for root in self.roots)

    def _root(self, alias: str | None) -> Path | None:
        key = (alias or "").casefold().strip()
        aliases = {"documentos": "documents", "downloads": "downloads", "desktop": "desktop",
                   "area de trabalho": "desktop", "projeto naty": "naty", "naty": "naty"}
        key = aliases.get(key, key)
        for root in self.roots:
            if root.name.casefold() == key or (key == "naty" and root.name.casefold().startswith("naty")):
                return root
        return None

    def open_folder(self, alias: str) -> ToolResult:
        root = self._root(alias)
        if not root:
            return ToolResult(False, f"A pasta {alias} não está entre as raízes permitidas.", type="file_error", error="root_not_allowed")
        try:
            self.opener(str(root))
            return ToolResult(True, f"Abri {root.name}.", {"path": str(root)}, type="folder_opened")
        except OSError as exc:
            return ToolResult(False, f"Não consegui abrir a pasta: {exc}", type="file_error", error=str(exc))

    def find(self, query: str, root_alias: str | None = None, recent: bool = False) -> ToolResult:
        query = query.strip().strip('"')
        requested = Path(os.path.expandvars(query)).expanduser()
        if requested.is_absolute():
            if not requested.exists() or not self._allowed(requested):
                return ToolResult(False, "Esse caminho está fora das raízes permitidas ou não existe.", type="file_error", error="path_not_allowed")
            items = [requested]
        else:
            selected = self._root(root_alias) if root_alias else None
            search_roots = (selected,) if selected else self.roots
            if root_alias and not selected:
                return ToolResult(False, "A raiz solicitada não está permitida.", type="file_error", error="root_not_allowed")
            items, scanned = [], 0
            needle = query.casefold()
            for root in search_roots:
                for current, directories, files in os.walk(root):
                    relative_depth = len(Path(current).relative_to(root).parts)
                    directories[:] = [d for d in directories if not d.startswith(".") and relative_depth < self.MAX_DEPTH]
                    for name in files:
                        scanned += 1
                        if not needle or needle in name.casefold(): items.append(Path(current) / name)
                        if scanned >= self.MAX_SCANNED or len(items) >= self.MAX_RESULTS: break
                    if scanned >= self.MAX_SCANNED or len(items) >= self.MAX_RESULTS: break
                if scanned >= self.MAX_SCANNED or len(items) >= self.MAX_RESULTS: break
        if recent: items.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        else: items.sort(key=lambda path: path.name.casefold())
        payload = [{"name": path.name, "path": str(path), "modified_at": datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")}
                   for path in items[:10]]
        if not payload: return ToolResult(True, "Não encontrei arquivos com esse nome nas raízes permitidas.", {"files": []}, type="file_list")
        if self.context is not None: self.context.state["last_file"] = payload[0]["path"]
        return ToolResult(True, f"Encontrei {len(payload)} arquivo(s). O primeiro é {payload[0]['name']}.", {"files": payload},
                          type="file_list", ui_hint={"mode": "context", "panel": "files", "title": "Arquivos"})

    def open_last(self) -> ToolResult:
        value = self.context.state.get("last_file") if self.context is not None else None
        path = Path(value).resolve() if value else None
        if not path or not path.is_file() or not self._allowed(path):
            return ToolResult(False, "Primeiro peça para eu encontrar um arquivo.", type="file_error", error="no_file_context")
        try:
            self.opener(str(path))
            return ToolResult(True, f"Abri {path.name}.", {"path": str(path)}, type="file_opened")
        except OSError as exc:
            return ToolResult(False, f"Não consegui abrir o arquivo: {exc}", type="file_error", error=str(exc))

    def resolve_for_delete(self, query: str) -> Path | None:
        requested = Path(os.path.expandvars(query.strip().strip('"'))).expanduser()
        if requested.is_absolute():
            candidate = requested.resolve()
            return candidate if candidate.is_file() and self._allowed(candidate) else None
        result = self.find(query)
        files = result.data.get("files", []) if result.ok and isinstance(result.data, dict) else []
        return Path(files[0]["path"]).resolve() if len(files) == 1 else None

    def request_delete(self, query: str) -> ToolResult:
        path = self.resolve_for_delete(query)
        if not path:
            return ToolResult(False, "Não encontrei um único arquivo permitido com esse nome.", type="file_error", error="file_ambiguous")
        return ToolResult(False, f"Isso enviará {path.name} para a Lixeira. Diga 'sim' para confirmar ou 'cancelar'.",
                          {"path": str(path), "requires_confirmation": True}, type="file_delete_confirmation",
                          error="confirmation_required")

    def recycle_confirmed(self, path_value: str) -> ToolResult:
        path = Path(path_value).resolve()
        if not path.is_file() or not self._allowed(path):
            return ToolResult(False, "O arquivo não existe ou saiu das raízes permitidas.", type="file_error", error="path_not_allowed")
        try:
            self.recycler(path)
            return ToolResult(True, f"Enviei {path.name} para a Lixeira.", {"path": str(path)}, type="file_recycled")
        except OSError as exc:
            return ToolResult(False, f"Não consegui enviar o arquivo para a Lixeira: {exc}", type="file_error", error=str(exc))

    @staticmethod
    def _open(target: str) -> None:
        if os.name != "nt": raise OSError("Abertura de arquivos disponível somente no Windows.")
        os.startfile(target)  # type: ignore[attr-defined]

    @staticmethod
    def _recycle(path: Path) -> None:
        if os.name != "nt": raise OSError("Lixeira disponível somente no Windows.")
        import ctypes
        from ctypes import wintypes
        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                        ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", wintypes.BOOL),
                        ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]
        operation = SHFILEOPSTRUCTW(None, 3, str(path) + "\0\0", None, 0x40 | 0x10 | 0x4 | 0x400, False, None, None)
        result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(operation))
        if result or operation.fAnyOperationsAborted: raise OSError(f"Windows recusou a operação ({result}).")
