from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import ssl
import threading
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ALLOWED_HOSTS = {"alphacephei.com", "huggingface.co", "cdn-lfs.huggingface.co", "objects.githubusercontent.com", "github.com"}


@dataclass(slots=True)
class DownloadSpec:
    name: str
    url: str
    size_bytes: int | None
    license: str
    sha256: str | None = None


class DownloadCancelled(RuntimeError): pass


class DownloadManager:
    def __init__(self, allowed_hosts: set[str] | None = None):
        self.allowed_hosts = allowed_hosts or ALLOWED_HOSTS

    def validate(self, spec: DownloadSpec) -> None:
        parsed = urlparse(spec.url)
        if parsed.scheme != "https" or (parsed.hostname or "").lower() not in self.allowed_hosts:
            raise ValueError("Origem de download não permitida.")
        if spec.sha256 and (len(spec.sha256) != 64 or any(c not in "0123456789abcdefABCDEF" for c in spec.sha256)):
            raise ValueError("Checksum SHA-256 inválido.")

    def download(self, spec: DownloadSpec, destination: str | Path, progress=None,
                 cancel: threading.Event | None = None) -> Path:
        self.validate(spec)
        target = Path(destination); target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(target.suffix + ".part")
        digest, written = hashlib.sha256(), 0
        request = Request(spec.url, headers={"User-Agent": "Naty/2.0 model installer"})
        try:
            with urlopen(request, timeout=30, context=ssl.create_default_context()) as response, partial.open("wb") as output:
                total = int(response.headers.get("Content-Length") or spec.size_bytes or 0)
                while True:
                    if cancel and cancel.is_set(): raise DownloadCancelled("Download cancelado.")
                    chunk = response.read(1024 * 256)
                    if not chunk: break
                    output.write(chunk); digest.update(chunk); written += len(chunk)
                    if progress: progress(written, total)
                output.flush()
            if spec.size_bytes and written < spec.size_bytes * 0.80:
                raise ValueError("Arquivo baixado é muito menor que o tamanho publicado.")
            if spec.sha256 and digest.hexdigest().lower() != spec.sha256.lower():
                raise ValueError("Checksum SHA-256 não confere.")
            partial.replace(target)
            return target
        except Exception:
            partial.unlink(missing_ok=True)
            raise
