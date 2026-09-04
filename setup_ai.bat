@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ambiente virtual nao encontrado. Execute setup.bat primeiro.
  exit /b 1
)
".venv\Scripts\python.exe" -m scripts.setup_ai
endlocal
