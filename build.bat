@echo off
REM ============================================================
REM  build.bat -- builds dist\OrdisMarket.exe
REM
REM  Ordis: "Compiling myself into a single, portable executable.
REM          This is either impressive or deeply unsettling."
REM ============================================================

setlocal

REM Same reasoning as run.bat: force CWD to this script's folder so
REM PyInstaller finds app\main.py no matter how build.bat was launched
REM (shortcut, admin prompt, CI runner, etc.).
cd /d "%~dp0"

echo [Ordis Market] Checking for Python...
where python >nul 2>nul
if errorlevel 1 (
    echo [Ordis Market] ERROR: Python was not found on PATH.
    echo Operator, please install Python 3.11+ before building.
    exit /b 1
)

echo [Ordis Market] Installing/upgrading dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [Ordis Market] ERROR: dependency installation failed.
    exit /b 1
)

echo [Ordis Market] Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist OrdisMarket.spec del /q OrdisMarket.spec

echo [Ordis Market] Building OrdisMarket.exe with PyInstaller...
REM No --add-data is needed: the app never reads data\sample_inventory.json
REM at runtime (it's just a manual reference file for IMPORT INVENTORY),
REM and OrdisMarket creates its own data\/logs\ folders next to the .exe
REM automatically on first launch -- see app/config/settings.py for why
REM that's anchored to the .exe's real location, not a temp folder.
python -m PyInstaller ^
    --name OrdisMarket ^
    --onefile ^
    --windowed ^
    app\main.py

if errorlevel 1 (
    echo [Ordis Market] ERROR: PyInstaller build failed. I have filed a complaint. With myself.
    exit /b 1
)

echo.
echo [Ordis Market] Build complete: dist\OrdisMarket.exe
echo Operator, I have survived another compilation.
echo On first launch, OrdisMarket.exe creates its own data\ and logs\
echo folders right next to itself -- nothing extra needs to be copied in,
echo and everything it creates will still be there on your next launch.
endlocal
