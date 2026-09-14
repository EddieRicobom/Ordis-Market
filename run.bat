@echo off
REM ============================================================
REM  run.bat -- double-click launcher for running from source.
REM
REM  Ordis: "Click. That is the entire procedure. I have handled
REM          the rest."
REM ============================================================

setlocal

REM Force the working directory to this script's own folder, regardless
REM of how it was launched (shortcut, "Run as administrator", a scheduled
REM task, etc. can all start us in C:\Windows\System32 otherwise).
REM Ordis: "I refuse to run from System32. That is not my home."
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [Ordis Market] ERROR: Python was not found on PATH.
    echo Operator, please install Python 3.11+ first: https://www.python.org/downloads/
    pause
    exit /b 1
)

python run.py
if errorlevel 1 (
    echo.
    echo [Ordis Market] Something went wrong. See above for details.
    pause
)

endlocal
