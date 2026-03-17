@echo off
REM ============================================================
REM  Moskowitz Gaming — Windows Build Script
REM  Run this on a Windows machine to produce GamingHUD.exe
REM ============================================================

echo.
echo  ========================================
echo   Moskowitz Gaming - Build Script
echo  ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found. Install Python 3.10+ from python.org
    pause
    exit /b 1
)

REM Install dependencies
echo  [1/3] Installing dependencies...
pip install -r gaming_hud_requirements.txt
if errorlevel 1 (
    echo  ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

REM Optional: install Pillow for .ico generation
pip install Pillow >nul 2>&1

REM Build
echo.
echo  [2/3] Building executable...
python build_hud.py
if errorlevel 1 (
    echo  ERROR: Build failed.
    pause
    exit /b 1
)

echo.
echo  [3/3] Done! Your executable is in the dist\ folder.
echo.
echo  To run:  dist\MoskowitzGaming.exe
echo.
pause
