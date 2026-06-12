# Greenline local dev launcher (Windows).
# Starts the FastAPI backend and the Vite dev server, opens the browser.
# Usage: .\scripts\dev.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent

$python = Join-Path $root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Backend venv missing — creating it..."
    python -m venv (Join-Path $root "backend\.venv")
    & $python -m pip install -e (Join-Path $root "backend")
}

if (-not (Test-Path (Join-Path $root "frontend\node_modules"))) {
    Write-Host "Frontend deps missing — installing..."
    Push-Location (Join-Path $root "frontend"); npm install; Pop-Location
}

Write-Host "Starting backend on http://127.0.0.1:8537 ..."
$backend = Start-Process -PassThru -WorkingDirectory $root $python -ArgumentList "-m", "greenline.main"

Write-Host "Starting frontend on http://localhost:5173 ..."
$frontend = Start-Process -PassThru -WorkingDirectory (Join-Path $root "frontend") "cmd" -ArgumentList "/c", "npm run dev"

Start-Sleep -Seconds 2
Start-Process "http://localhost:5173"

Write-Host "Greenline is up. Press Enter to stop both servers."
Read-Host | Out-Null
Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
