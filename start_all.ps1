# PII Guard - Unified Startup Script
# Starts all system-level monitors

Clear-Host

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  PII Guard - Complete Protection System" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment if present
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    & ".\venv\Scripts\Activate.ps1"
}

Write-Host "Starting all monitors..." -ForegroundColor Green
Write-Host ""

python start_all.py

Write-Host ""
Write-Host "Stopped." -ForegroundColor Yellow
pause

