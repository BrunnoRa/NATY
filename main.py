from __future__ import annotations

import argparse

from config import Settings
from core.assistant import NatyAssistant


def cli(assistant: NatyAssistant, command: str | None = None) -> int:
    if command:
        print(assistant.handle(command)); return 0
    print("Naty CLI. Digite 'sair' para encerrar.")
    while True:
        try: text = input("> ").strip()
        except (EOFError, KeyboardInterrupt): break
        if text.lower() in {"sair", "exit", "quit"}: break
        if text: print(assistant.handle(text))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Naty — agente pessoal local")
    parser.add_argument("--cli", action="store_true", help="executa sem interface gráfica")
    parser.add_argument("--command", help="executa um comando e encerra")
    parser.add_argument("--no-tray", action="store_true", help="desativa o ícone de bandeja")
    args = parser.parse_args()
    assistant = NatyAssistant(Settings.load())
    if args.cli or args.command: return cli(assistant, args.command)
    try:
        from ui.main_window import MainWindow
        MainWindow(assistant, use_tray=not args.no_tray).run(); return 0
    except Exception as exc:
        assistant.logger.exception("Falha ao iniciar interface")
        print(f"Não foi possível iniciar a interface: {exc}")
        print("Use: python main.py --cli")
        return 1


if __name__ == "__main__": raise SystemExit(main())
