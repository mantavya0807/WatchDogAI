# PII Guard - Combined Monitor Quick Start
# Runs both clipboard and keystroke protection together

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  PII Guard - Complete Protection" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment is activated
if ($env:VIRTUAL_ENV) {
    Write-Host "[OK] Virtual environment is active" -ForegroundColor Green
} else {
    Write-Host "[!] Activating virtual environment..." -ForegroundColor Yellow
    & ".\venv\Scripts\Activate.ps1"
}

Write-Host ""
Write-Host "Starting combined protection..." -ForegroundColor Green
Write-Host ""
Write-Host "This will start BOTH:" -ForegroundColor Yellow
Write-Host "  - Clipboard monitor (copy/paste protection)" -ForegroundColor White
Write-Host "  - Keystroke monitor (typing warnings)" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop both" -ForegroundColor Yellow
Write-Host ""

python combined_monitor.py
