param(
    [switch]$StartWithWindows,
    [string]$PayloadPath = (Join-Path $PSScriptRoot "Naty")
)

$ErrorActionPreference = "Stop"
$installRoot = Join-Path $env:LOCALAPPDATA "Programs\NATY"
$expectedRoot = [System.IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA "Programs\NATY"))
$resolvedRoot = [System.IO.Path]::GetFullPath($installRoot)
if ($resolvedRoot -ne $expectedRoot) { throw "Destino de instalação inválido." }
if (-not (Test-Path -LiteralPath (Join-Path $PayloadPath "Naty.exe"))) {
    throw "Naty.exe não foi encontrado em $PayloadPath"
}

Get-Process -Name "Naty" -ErrorAction SilentlyContinue | Stop-Process -Force
if (Test-Path -LiteralPath $resolvedRoot) {
    Remove-Item -LiteralPath $resolvedRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $resolvedRoot -Force | Out-Null
Copy-Item -Path (Join-Path $PayloadPath "*") -Destination $resolvedRoot -Recurse -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "uninstall_naty.ps1") -Destination $resolvedRoot -Force
$iconPath = Join-Path $resolvedRoot "_internal\assets\naty.ico"
if (-not (Test-Path -LiteralPath $iconPath)) { throw "Ícone instalado não encontrado em $iconPath" }

$shell = New-Object -ComObject WScript.Shell
$desktopShortcut = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "Naty.lnk"))
$desktopShortcut.TargetPath = Join-Path $resolvedRoot "Naty.exe"
$desktopShortcut.WorkingDirectory = $resolvedRoot
$desktopShortcut.IconLocation = $iconPath + ",0"
$desktopShortcut.Description = "Naty - agente pessoal local"
$desktopShortcut.Save()

$menuRoot = Join-Path ([Environment]::GetFolderPath("Programs")) "NATY"
New-Item -ItemType Directory -Path $menuRoot -Force | Out-Null
$menuShortcut = $shell.CreateShortcut((Join-Path $menuRoot "Naty.lnk"))
$menuShortcut.TargetPath = Join-Path $resolvedRoot "Naty.exe"
$menuShortcut.WorkingDirectory = $resolvedRoot
$menuShortcut.IconLocation = $iconPath + ",0"
$menuShortcut.Save()
$uninstallShortcut = $shell.CreateShortcut((Join-Path $menuRoot "Desinstalar Naty.lnk"))
$uninstallShortcut.TargetPath = "powershell.exe"
$uninstallShortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $resolvedRoot "uninstall_naty.ps1") + '"'
$uninstallShortcut.IconLocation = $iconPath + ",0"
$uninstallShortcut.Save()

$runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
if ($StartWithWindows) {
    New-ItemProperty -Path $runKey -Name "Naty" -Value ('"' + (Join-Path $resolvedRoot "Naty.exe") + '"') -PropertyType String -Force | Out-Null
}

$iconRefresh = Join-Path $env:SystemRoot "System32\ie4uinit.exe"
if (Test-Path -LiteralPath $iconRefresh) {
    Start-Process -FilePath $iconRefresh -ArgumentList "-show" -WindowStyle Hidden -Wait
}

Write-Host "Naty instalada em $resolvedRoot"
Write-Host "Atalho criado na Área de Trabalho e no menu Iniciar."
