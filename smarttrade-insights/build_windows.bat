@echo off
REM ============================================================
REM  SmartTrade Insights - Windows Build Script
REM  Produces:  dist\SmartTradeInsights\SmartTradeInsights.exe
REM ============================================================

SETLOCAL ENABLEDELAYEDEXPANSION

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   SmartTrade Insights - Windows Build         ║
echo  ╚══════════════════════════════════════════════╝
echo.

REM ── Check Python ─────────────────────────────────────────────────────────────
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo  [ERROR] Python not found in PATH. Please install Python 3.10+.
    pause & exit /b 1
)

REM ── Check / install PyInstaller ───────────────────────────────────────────────
python -c "import PyInstaller" >nul 2>&1
IF ERRORLEVEL 1 (
    echo  [INFO] Installing PyInstaller…
    pip install pyinstaller>=6.3.0
)

REM ── Install / verify requirements ────────────────────────────────────────────
echo  [INFO] Installing requirements…
pip install -r requirements.txt --quiet
IF ERRORLEVEL 1 (
    echo  [ERROR] Failed to install requirements.
    pause & exit /b 1
)

REM ── Clean previous build ─────────────────────────────────────────────────────
echo  [INFO] Cleaning previous build artifacts…
IF EXIST dist\SmartTradeInsights  rd /s /q dist\SmartTradeInsights
IF EXIST build                     rd /s /q build

REM ── Run PyInstaller ──────────────────────────────────────────────────────────
echo  [INFO] Running PyInstaller…
pyinstaller SmartTradeInsights.spec --noconfirm --clean
IF ERRORLEVEL 1 (
    echo  [ERROR] PyInstaller failed. Check output above.
    pause & exit /b 1
)

REM ── Verify output ─────────────────────────────────────────────────────────────
IF NOT EXIST dist\SmartTradeInsights\SmartTradeInsights.exe (
    echo  [ERROR] EXE not found after build.
    pause & exit /b 1
)

REM ── Package into a ZIP ───────────────────────────────────────────────────────
echo  [INFO] Creating release ZIP…
powershell -Command ^
  "Compress-Archive -Path 'dist\SmartTradeInsights' -DestinationPath 'dist\SmartTradeInsights_v1.0.0_Windows.zip' -Force"

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   Build complete!                             ║
echo  ║                                               ║
echo  ║   EXE : dist\SmartTradeInsights\             ║
echo  ║         SmartTradeInsights.exe                ║
echo  ║   ZIP : dist\SmartTradeInsights_v1.0.0_      ║
echo  ║         Windows.zip                           ║
echo  ╚══════════════════════════════════════════════╝
echo.

pause
