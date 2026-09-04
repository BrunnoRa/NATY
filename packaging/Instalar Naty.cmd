@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_naty.ps1"
if errorlevel 1 pause
