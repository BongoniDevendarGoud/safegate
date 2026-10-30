@echo off
title SafeGate 7-Layer OSI Security Appliance
echo =====================================================================
echo  SafeGate -- 7-Layer OSI Security Screening Appliance and CLI
echo =====================================================================
echo.

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set PYTHON_EXEC=%LOCALAPPDATA%\Programs\Python\Python314\python.exe
) else (
    set PYTHON_EXEC=python
)

set SAFEGATE_MOCK_MODEL=true

echo Choose an action:
echo  [1] Scan authentic clean video (samples\sample_clean.mp4)
echo  [2] Scan synthetic deepfake video (samples\sample_malicious_deepfake.mp4)
echo  [3] Verify cryptographic SHA-256 audit hash chain
echo  [4] Display system metrics and telemetry
echo  [5] Launch headless server daemon (http://localhost:8000)
echo  [6] Run full test suite (pytest)
echo.
set /p opt="Enter selection [1-6] (default: 1): "

if "%opt%"=="2" (
    "%PYTHON_EXEC%" cli.py scan samples\sample_malicious_deepfake.mp4
) else if "%opt%"=="3" (
    "%PYTHON_EXEC%" cli.py audit
) else if "%opt%"=="4" (
    "%PYTHON_EXEC%" cli.py stats
) else if "%opt%"=="5" (
    "%PYTHON_EXEC%" cli.py serve
) else if "%opt%"=="6" (
    "%PYTHON_EXEC%" -m pytest tests/ -v
) else (
    "%PYTHON_EXEC%" cli.py scan samples\sample_clean.mp4
)

echo.
pause
