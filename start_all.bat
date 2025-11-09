@echo off
REM PII Guard - Unified Startup Script
REM Starts all system-level monitors

echo ===============================================
echo   PII Guard - Complete Protection System
echo ===============================================
echo.

REM Activate virtual environment if present
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo Starting all monitors...
echo.

python start_all.py

pause

