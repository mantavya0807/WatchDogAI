@echo off
REM PII Guard - Keystroke Monitor Quick Start

echo ===============================================
echo   PII Guard - Keystroke Monitor
echo ===============================================
echo.

REM Check for mode argument
set MODE=%1
if "%MODE%"=="" set MODE=cli

REM Activate virtual environment
if not defined VIRTUAL_ENV (
    echo [!] Activating virtual environment...
    call venv\Scripts\activate.bat
)

echo.

REM Run based on mode
if /i "%MODE%"=="tray" (
    echo Starting system tray monitor...
    echo Look for keyboard icon in system tray
    echo.
    python tray_keystroke_monitor.py
) else if /i "%MODE%"=="test" (
    echo Running tests...
    echo.
    python test_keystroke.py --basic
) else (
    echo Starting command-line monitor...
    echo Press Ctrl+C to stop
    echo.
    python keystroke_monitor.py
)

pause
