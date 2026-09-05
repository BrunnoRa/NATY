from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
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
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.02)
    response = json.loads(raw.decode("utf-8"))
    assert response["protocol"] == 1 and response["request_id"] == request_id, response
    return response


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core", help="Executável Naty.Core empacotado; omita para usar Python.")
    args = parser.parse_args()
    pipe_name = f"Naty.Core.smoke.{uuid4().hex}"
    pipe = rf"\\.\pipe\{pipe_name}"
    command = [args.core, "--pipe", pipe_name] if args.core else [sys.executable, str(ROOT / "core_host.py"), "--pipe", pipe_name]
    with tempfile.TemporaryDirectory() as local_data:
        environment = os.environ.copy()
        if args.core:
            environment["LOCALAPPDATA"] = local_data
        process = subprocess.Popen(command, cwd=Path(args.core).parent if args.core else ROOT, env=environment)
        try:
            deadline = time.monotonic() + 15
            while True:
                try:
                    pong = exchange("ping", pipe=pipe)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.1)
            dashboard = exchange("dashboard", pipe=pipe)
            assert pong["type"] == "pong"
            assert dashboard["type"] == "dashboard"
            assert {"providers", "metrics", "graph", "tasks"} <= dashboard["payload"].keys()
            greeting = exchange("user_input", {"text": "Oi Naty"}, pipe)
            assert greeting["payload"]["success"] and greeting["payload"]["type"] == "chat"
            assert greeting["payload"]["ui"]["mode"] == "brain"
            diagnostics = exchange("diagnostics", {"hotkey": "registered"}, pipe)
            assert diagnostics["type"] == "diagnostics"
            component_names = {item["name"] for item in diagnostics["payload"]["items"]}
            assert {
                "Desktop",
                "Core",
                "Pipe",
                "SQLite",
                "Whisper",
                "Piper",
                "Google",
                "Sync",
                "Hotkey",
            } <= component_names
            precision = exchange("voice_precision_status", pipe=pipe)
            assert precision["type"] == "voice_precision_status"
            assert {"state", "active", "transcription", "wer", "latency_ms"} <= precision["payload"].keys()
            stopped = exchange("shutdown", pipe=pipe)
            assert stopped["type"] == "shutdown_ack"
            process.wait(timeout=8)
            print(
                "OK: Named Pipe v1, ping, dashboard, resposta estruturada, "
                "diagnóstico, teste de precisão e shutdown limpo."
            )
            return 0
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=3)


if __name__ == "__main__":
    raise SystemExit(main())
