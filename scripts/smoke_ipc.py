from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
PIPE = r"\\.\pipe\Naty.Core.v1"


def exchange(type_: str, payload: dict | None = None, pipe: str | None = None) -> dict:
    request_id = uuid4().hex
    message = {"protocol": 1, "type": type_, "request_id": request_id, "payload": payload or {}}
    deadline = time.monotonic() + 2
    while True:
        try:
            with open(pipe or PIPE, "r+b", buffering=0) as stream:
                stream.write(json.dumps(message, ensure_ascii=False).encode("utf-8") + b"\n")
                raw = stream.readline()
            break
        except FileNotFoundError:
            if time.monotonic() >= deadline: raise
            time.sleep(0.02)
    response = json.loads(raw.decode("utf-8"))
    assert response["protocol"] == 1 and response["request_id"] == request_id, response
    return response


def main() -> int:
    pipe_name = f"Naty.Core.smoke.{uuid4().hex}"
    pipe = rf"\\.\pipe\{pipe_name}"
    process = subprocess.Popen([sys.executable, str(ROOT / "core_host.py"), "--pipe", pipe_name], cwd=ROOT)
    try:
        deadline = time.monotonic() + 8
        while True:
            try:
                pong = exchange("ping", pipe=pipe)
                break
            except OSError:
                if time.monotonic() >= deadline: raise
                time.sleep(0.1)
        dashboard = exchange("dashboard", pipe=pipe)
        assert pong["type"] == "pong"
        assert dashboard["type"] == "dashboard"
        assert {"providers", "metrics", "graph", "tasks"} <= dashboard["payload"].keys()
        greeting = exchange("user_input", {"text": "Oi Naty"}, pipe)
        assert greeting["payload"]["success"] and greeting["payload"]["type"] == "chat"
        assert greeting["payload"]["ui"]["mode"] == "brain"
        stopped = exchange("shutdown", pipe=pipe)
        assert stopped["type"] == "shutdown_ack"
        process.wait(timeout=5)
        print("OK: Named Pipe v1, ping, dashboard, resposta estruturada e shutdown limpo.")
        return 0
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=3)


if __name__ == "__main__":
    raise SystemExit(main())
