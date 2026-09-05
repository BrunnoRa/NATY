from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import time

import psutil

from config import Settings
from voice.vosk_stt import VoskSTT
from voice.whisper_cpp import WhisperCppSTT


def words(text: str) -> list[str]:
    return re.findall(r"[\wÀ-ÿ]+", text.casefold())


def word_error_rate(expected: str, actual: str) -> float | None:
    reference, hypothesis = words(expected), words(actual)
    if not reference: return None
    previous = list(range(len(hypothesis) + 1))
    for index, reference_word in enumerate(reference, 1):
        current = [index]
        for j, hypothesis_word in enumerate(hypothesis, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (reference_word != hypothesis_word)))
        previous = current
    return previous[-1] / len(reference)


def tree_rss() -> int:
    process = psutil.Process()
    return sum(item.memory_info().rss for item in [process, *process.children(recursive=True)] if item.is_running())


def measure(name: str, provider, wav: Path, expected: str) -> dict:
    if not provider.available(): return {"provider": name, "available": False}
    before = tree_rss(); started = time.perf_counter()
    output = provider.transcribe_wav(wav)
    latency = (time.perf_counter() - started) * 1000; after = tree_rss()
    return {"provider": name, "available": True, "output": output,
            "wer": word_error_rate(expected, output), "latency_ms": round(latency, 2),
            "ram_delta_mib": round((after - before) / 1024 / 1024, 2)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Compara providers STT usando exatamente o mesmo WAV.")
    parser.add_argument("wav", type=Path)
    parser.add_argument("--expected", default="")
    parser.add_argument("--whisper-exe", default="")
    parser.add_argument("--base-model", default="")
    parser.add_argument("--small-model", default="")
    args = parser.parse_args()
    if not args.wav.is_file(): parser.error("WAV não encontrado")
    settings = Settings.load()
    executable = args.whisper_exe or settings.whisper_executable_path
    providers = [
        ("Vosk", VoskSTT(settings.vosk_model_path)),
        ("Whisper Base", WhisperCppSTT(executable, args.base_model)),
        ("Whisper Small", WhisperCppSTT(executable, args.small_model)),
    ]
    report = {"wav": str(args.wav.resolve()), "expected": args.expected,
              "results": [measure(name, provider, args.wav, args.expected) for name, provider in providers]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__": raise SystemExit(main())
