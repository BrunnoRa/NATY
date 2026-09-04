@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3.11 ou mais recente nao foi encontrado.
  echo Instale Python em https://www.python.org/downloads/windows/ e execute este arquivo novamente.
  pause
  exit /b 1
)
py -3 -m venv .venv
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
echo.
echo Instalacao concluida. Use run_naty.bat.
pause
