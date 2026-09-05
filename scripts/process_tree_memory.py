from __future__ import annotations

import argparse
import json
import time

import psutil


def snapshot(pid: int) -> dict:
    root = psutil.Process(pid)
    processes = [root, *root.children(recursive=True)]
    rows, rss, cpu = [], 0, 0.0
    for process in processes:
        try:
            memory = process.memory_info().rss; usage = process.cpu_percent(interval=None)
            rows.append({"pid": process.pid, "name": process.name(), "rss_mib": round(memory / 1024 / 1024, 2), "cpu_percent": usage})
            rss += memory; cpu += usage
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    return {"root_pid": pid, "processes": rows, "rss_mib": round(rss / 1024 / 1024, 2), "cpu_percent": round(cpu, 2)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Soma RAM/CPU do processo NATY e filhos recursivos.")
    parser.add_argument("pid", type=int); parser.add_argument("--watch-seconds", type=float, default=0)
    args = parser.parse_args(); deadline = time.monotonic() + max(0, args.watch_seconds)
    peak = snapshot(args.pid)
    while time.monotonic() < deadline:
        time.sleep(.25); current = snapshot(args.pid)
        if current["rss_mib"] > peak["rss_mib"]: peak = current
    print(json.dumps(peak, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
