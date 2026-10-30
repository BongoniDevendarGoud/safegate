@echo off
title SafeGate Automated Environment Setup
echo =====================================================================
echo    SafeGate -- One-Click Setup & Dependency Installation
echo =====================================================================
echo.

:: Detect Python
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set PYTHON_EXEC=%LOCALAPPDATA%\Programs\Python\Python314\python.exe
) else (
    set PYTHON_EXEC=python
)

echo [*] Checking Python installation...
"%PYTHON_EXEC%" --version
if errorlevel 1 (
    echo [ERROR] Python is not installed or not found on PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

:: Create Virtual Environment if not present
if not exist "venv" (
    echo [*] Creating virtual environment (venv)...
    "%PYTHON_EXEC%" -m venv venv
)

:: Activate Virtual Environment
echo [*] Activating virtual environment...
call venv\Scripts\activate.bat

:: Install Requirements
echo [*] Installing production dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

:: Initialize Environment File
if not exist ".env" (
    echo [*] Generating default .env from .env.example...
    copy .env.example .env >nul
)

:: Generate Test Samples if missing
if not exist "samples\sample_clean.mp4" (
    echo [*] Generating authentic and deepfake test media samples...
    python generate_test_samples.py
    if not exist "samples" mkdir samples
    copy sample_clean.mp4 samples\ >nul 2>&1
    copy sample_malicious_deepfake.mp4 samples\ >nul 2>&1
)

echo.
echo =====================================================================
echo  [SUCCESS] SafeGate is installed and ready for live execution!
echo =====================================================================
echo.
echo Run the following command to test SafeGate on sample media:
echo    python cli.py scan samples\sample_clean.mp4
echo    python cli.py scan samples\sample_malicious_deepfake.mp4
echo.
echo Or run the one-click launcher:
echo    run.bat
echo.
pause
