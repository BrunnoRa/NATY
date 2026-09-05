from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import os
import shutil
import time

import psutil


@dataclass(slots=True)
class SystemSnapshot:
    timestamp: str
    cpu_percent: float | None = None
    memory: dict = field(default_factory=dict)
    disk: dict = field(default_factory=dict)
    battery: dict = field(default_factory=dict)
    network: dict = field(default_factory=dict)
    top_processes: list[dict] = field(default_factory=list)
    uptime_seconds: int | None = None
    naty_process_tree: dict = field(default_factory=dict)
    gpu: dict = field(default_factory=lambda: {"state": "unavailable"})
    temperature: dict = field(default_factory=lambda: {"state": "unavailable"})


class SystemContextProvider:
    """Coleta barata e sob demanda; cada métrica falha de forma independente."""

    def __init__(self, process_id: int | None = None):
        self.process_id = process_id or os.getpid()

    @staticmethod
    def _mib(value: int | float) -> float:
        return round(float(value) / 1024 / 1024, 2)

    def collect(self) -> SystemSnapshot:
        snapshot = SystemSnapshot(datetime.now().astimezone().isoformat(timespec="seconds"))
        try:
            snapshot.cpu_percent = round(float(psutil.cpu_percent(interval=0.1)), 1)
        except Exception:
            pass
        try:
            memory = psutil.virtual_memory()
            snapshot.memory = {"total_mib": self._mib(memory.total), "used_mib": self._mib(memory.used),
                               "available_mib": self._mib(memory.available), "percent": round(float(memory.percent), 1)}
        except Exception:
            snapshot.memory = {"state": "unavailable"}
        try:
            anchor = Path.cwd().anchor or Path.home().anchor
            disk = shutil.disk_usage(anchor)
            snapshot.disk = {"root": anchor, "total_mib": self._mib(disk.total), "used_mib": self._mib(disk.used),
                             "free_mib": self._mib(disk.free), "percent": round(disk.used / max(1, disk.total) * 100, 1)}
        except Exception:
            snapshot.disk = {"state": "unavailable"}
        try:
            battery = psutil.sensors_battery()
            snapshot.battery = ({"state": "unavailable"} if battery is None else
                                {"percent": round(float(battery.percent), 1), "plugged": bool(battery.power_plugged),
                                 "seconds_left": None if battery.secsleft < 0 else int(battery.secsleft)})
        except Exception:
            snapshot.battery = {"state": "unavailable"}
        try:
            interfaces = psutil.net_if_stats()
            counters = psutil.net_io_counters()
            snapshot.network = {"connected": any(item.isup for item in interfaces.values()),
                                "interfaces_up": sum(1 for item in interfaces.values() if item.isup),
                                "bytes_sent": int(counters.bytes_sent), "bytes_received": int(counters.bytes_recv)}
        except Exception:
            snapshot.network = {"state": "unavailable"}
        try:
            snapshot.uptime_seconds = max(0, int(time.time() - psutil.boot_time()))
        except Exception:
            pass
        snapshot.top_processes = self._top_processes()
        snapshot.naty_process_tree = self._naty_tree()
        return snapshot

    def _top_processes(self) -> list[dict]:
        rows = []
        try:
            for process in psutil.process_iter(["pid", "name", "memory_info"]):
                try:
                    info = process.info
                    rows.append({"pid": int(info["pid"]), "name": info.get("name") or "Processo",
                                 "ram_mib": self._mib(info["memory_info"].rss)})
                except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError, AttributeError):
                    continue
        except Exception:
            return []
        return sorted(rows, key=lambda item: item["ram_mib"], reverse=True)[:5]

    def _naty_tree(self) -> dict:
        try:
            root = psutil.Process(self.process_id)
            processes = [root, *root.children(recursive=True)]
            names, rss = [], 0
            for process in processes:
                try:
                    names.append(process.name())
                    rss += process.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return {"processes": len(names), "names": names, "ram_mib": self._mib(rss)}
        except Exception:
            return {"state": "unavailable", "processes": 0, "names": [], "ram_mib": None}
