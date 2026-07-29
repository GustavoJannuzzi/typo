# Sobe a interface local em http://127.0.0.1:7860 (Windows / PowerShell)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "venv nao encontrado. Rode:"
    Write-Host "  python -m venv .venv"
    Write-Host "  .\.venv\Scripts\python.exe -m pip install -e ."
    exit 1
}
& $py -m app.ui @args
