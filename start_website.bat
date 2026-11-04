@echo off
title SafeGate Sentinel 24 FPS Web Gateway
echo =====================================================================
echo    SafeGate Sentinel -- Launching 24 FPS Web Gateway
echo =====================================================================
echo.
cd /d "%~dp0"

if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set PYTHON_EXEC=%LOCALAPPDATA%\Programs\Python\Python314\python.exe
) else (
    set PYTHON_EXEC=python
)

set SAFEGATE_MOCK_MODEL=true

echo [*] Starting SafeGate server on port 8000...
echo [*] Opening website in your default browser...
start "" "http://localhost:8000"

"%PYTHON_EXEC%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
