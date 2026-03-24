@echo off
:: TradeMe — Windows one-click build launcher
:: Double-click this file to build TradeMe.exe

title TradeMe Build

cd /d "%~dp0"

echo.
echo  TradeMe Build Script
echo  --------------------
echo.

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found on PATH.
    echo  Install Python 3.10+ from https://python.org and try again.
    echo.
    pause
    exit /b 1
)

:: Run the build
python build.py
if errorlevel 1 (
    echo.
    echo  Build failed. See error above.
    pause
    exit /b 1
)

pause
