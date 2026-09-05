from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

import psutil

from database.connection import Database
from database.migrations import migrate
from scripts.smoke_ipc import exchange
from sync.manager import SyncManager
from sync.models import DeviceIdentity


ROOT = Path(__file__).resolve().parents[1]


def tree_metrics(pid: int) -> dict:
    root = psutil.Process(pid)
    processes = [root, *root.children(recursive=True)]
    for process in processes:
        try: process.cpu_percent(None)
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    time.sleep(0.5)
    rss = 0
    cpu = 0.0
    names = []
    for process in processes:
        try:
            rss += process.memory_info().rss
            cpu += process.cpu_percent(None)
            names.append(process.name())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return {"ram_mib": round(rss / 1024 / 1024, 2), "cpu_percent": round(cpu, 2),
            "processes": len(names), "names": names}


def request_metrics(pid: int, text: str, timeout: float = 35) -> dict:
    started = time.perf_counter()
    response = exchange("user_input", {"text": text})
    elapsed = (time.perf_counter() - started) * 1000
    return {**tree_metrics(pid), "latency_ms": round(elapsed, 2),
            "success": bool(response["payload"].get("success"))}


def sync_metrics(root: Path) -> dict:
    database = Database(root / "sync-device" / "naty.db")
    migrate(database)
    identity = DeviceIdentity.load_or_create(root / "sync-device" / "identity.json", "benchmark")
    manager = SyncManager(database, root / "NatySync", identity)
    task_id = database.execute("INSERT INTO tasks(title) VALUES('Benchmark sync')")
    started = time.perf_counter()
    manager.record("task", task_id, "create", dict(database.one("SELECT * FROM tasks WHERE id=?", (task_id,))))
    result = manager.sync_now()
    return {"latency_ms": round((time.perf_counter() - started) * 1000, 2), "status": result["status"]}


def main() -> int:
    executable = ROOT / "dist" / "NatyHybrid" / "Naty.exe"
    if not executable.is_file():
        raise FileNotFoundError("Execute scripts/build_windows.py antes do benchmark híbrido.")
    with tempfile.TemporaryDirectory() as temporary:
        environment = os.environ.copy()
        environment["LOCALAPPDATA"] = temporary
        process = subprocess.Popen([str(executable)], cwd=executable.parent, env=environment)
        try:
            deadline = time.monotonic() + 20
            while True:
                try:
                    exchange("ping")
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.1)
            time.sleep(2)
            result = {
                "idle": tree_metrics(process.pid),
                "brain": request_metrics(process.pid, "Oi Naty"),
                "context": request_metrics(process.pid, "O que eu tenho hoje?"),
                "research": request_metrics(process.pid, "Pesquisa novidades de inteligência artificial"),
                "sync_manager": sync_metrics(Path(temporary)),
                "whisper_loaded": {"measured": False, "reason": "requer fala controlada"},
                "transcription": {"measured": False, "reason": "requer fala controlada"},
                "piper": {"measured": False, "reason": "requer reprodução autorizada"},
            }
            exchange("shutdown")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        finally:
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
