@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" main.py
  exit /b 0
)
where pythonw >nul 2>nul
if %errorlevel%==0 (
  start "" pythonw main.py
  exit /b 0
)
echo A Naty ainda nao foi instalada. Execute setup_naty.bat primeiro.
pause
