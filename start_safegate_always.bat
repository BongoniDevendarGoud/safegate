@echo off
title SafeGate 2.0 — Persistent 24/7 Security Gateway
cd /d "%~dp0"

echo ==============================================================================
echo SafeGate 2.0 — Starting Always-Available In-Line AI Video Firewall...
echo ==============================================================================
echo.

set SAFEGATE_MOCK_MODEL=true
set USE_GEMINI=false

echo [*] Checking local Python environment...
python -c "import uvicorn, fastapi" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Installing required packages...
    pip install -r requirements.txt
)

echo [*] Launching SafeGate server on http://localhost:8000 ...
echo [*] Accessible on this machine and local network 24/7.
echo [*] Press Ctrl+C to stop.
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
