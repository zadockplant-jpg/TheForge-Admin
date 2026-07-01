# SendForge Admin EXE Builder v0.3.3
# Conservative full replacement: no regex parsing, no portable .venv assumptions.
$ErrorActionPreference = 'Stop'

Write-Host 'SendForge Admin EXE Builder' -ForegroundColor Cyan
Write-Host ('Building from: {0}' -f $PSScriptRoot) -ForegroundColor DarkGray
Set-Location -LiteralPath $PSScriptRoot

function Invoke-NativeChecked {
    param(
        [Parameter(Mandatory = $true)][string]$Exe,
        [Parameter(Mandatory = $true)][string[]]$Args
    )

    & $Exe @Args
    if ($LASTEXITCODE -ne 0) {
        throw ('Command failed with exit code {0}: {1} {2}' -f $LASTEXITCODE, $Exe, ($Args -join ' '))
    }
}

if (-not (Test-Path -LiteralPath 'app.py')) {
    throw 'app.py was not found. Run this from the SendForge Admin project folder.'
}

if (-not (Test-Path -LiteralPath 'requirements.txt')) {
    throw 'requirements.txt was not found. Run this from the SendForge Admin project folder.'
}

$PyLauncher = Get-Command py -ErrorAction SilentlyContinue
$PythonCommand = Get-Command python -ErrorAction SilentlyContinue

if ($PyLauncher) {
    $BasePythonExe = $PyLauncher.Source
    $BasePythonArgs = @('-3')
}
elseif ($PythonCommand) {
    $BasePythonExe = $PythonCommand.Source
    $BasePythonArgs = @()
}
else {
    throw 'Python was not found. Install Python 3.11+ from python.org, then rerun this script.'
}

$VenvPath = Join-Path $PSScriptRoot '.venv'
$VenvPython = Join-Path $VenvPath 'Scripts\python.exe'

# Recreate every time for reliability. Copied/moved virtual environments store
# absolute paths and are the source of the previous PyInstaller failures.
if (Test-Path -LiteralPath $VenvPath) {
    Write-Host 'Removing existing virtual environment...' -ForegroundColor Yellow
    Remove-Item -LiteralPath $VenvPath -Recurse -Force
}

Write-Host 'Creating virtual environment...' -ForegroundColor Yellow
Invoke-NativeChecked $BasePythonExe ($BasePythonArgs + @('-m', 'venv', $VenvPath))

if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw ('Virtual environment creation failed. Missing: {0}' -f $VenvPython)
}

Write-Host 'Installing build dependencies...' -ForegroundColor Yellow
Invoke-NativeChecked $VenvPython @('-m', 'pip', 'install', '--upgrade', 'pip')
Invoke-NativeChecked $VenvPython @('-m', 'pip', 'install', '-r', 'requirements.txt', 'pyinstaller')

Write-Host 'Building SendForge Admin.exe...' -ForegroundColor Yellow
Invoke-NativeChecked $VenvPython @(
    '-m', 'PyInstaller',
    '--noconfirm',
    '--clean',
    '--onefile',
    '--windowed',
    '--name', 'SendForge Admin',
    '--collect-all', 'customtkinter',
    'app.py'
)

$ExePath = Join-Path $PSScriptRoot 'dist\SendForge Admin.exe'
if (-not (Test-Path -LiteralPath $ExePath)) {
    throw ('Build finished but EXE was not found at {0}' -f $ExePath)
}

Write-Host ''
Write-Host 'DONE' -ForegroundColor Green
Write-Host 'EXE created at:' -ForegroundColor Green
Write-Host $ExePath -ForegroundColor White
Write-Host ''
Write-Host 'Run it by double-clicking dist\SendForge Admin.exe' -ForegroundColor Cyan
