# PII Guard - Start All Services
Clear-Host

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  PII Guard - Complete Protection" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Activate venv if present
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    & ".\venv\Scripts\Activate.ps1"
}

Write-Host "Starting monitors + notifications..." -ForegroundColor Green
Write-Host ""

python combined_monitor.py

Write-Host ""
Write-Host "Stopped." -ForegroundColor Yellow
pause