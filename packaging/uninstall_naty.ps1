$ErrorActionPreference = "Stop"
$installRoot = [System.IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA "Programs\NATY"))
$menuRoot = Join-Path ([Environment]::GetFolderPath("Programs")) "NATY"
$desktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "Naty.lnk"

Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "Naty" -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $desktopShortcut -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $menuRoot -Recurse -Force -ErrorAction SilentlyContinue
Get-Process -Name "Naty" -ErrorAction SilentlyContinue | Stop-Process -Force
Remove-Item -LiteralPath $installRoot -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Naty desinstalada. Seus dados em LOCALAPPDATA\NATY e o Vault do Obsidian foram preservados."
