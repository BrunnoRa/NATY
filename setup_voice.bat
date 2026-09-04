@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Execute setup_naty.bat primeiro.
  pause
  exit /b 1
)
echo A instalacao adicionara Vosk e sounddevice. O modelo pt-BR oficial de 31 MB so sera baixado apos confirmacao.
".venv\Scripts\python.exe" -m pip install -r requirements-voice.txt
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" scripts\setup_voice.py
pause
