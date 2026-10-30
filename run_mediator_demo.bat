@echo off
title SafeGate Global Internet Mediator Prototype Demo
echo =====================================================================
echo  SafeGate -- Global Internet Upload Mediator (College Prototype)
echo =====================================================================
echo.

set PYTHON_EXEC=python
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set PYTHON_EXEC=%LOCALAPPDATA%\Programs\Python\Python314\python.exe
)

echo Starting SafeGate Live Internet Mediator Prototype...
echo Running 3 real-world worldwide upload scenarios:
echo   1. User uploads clean media to internet   -^> Permitted (200 OK)
echo   2. User uploads harmful deepfake video    -^> Intercepted and Killed in Flight (403 Forbidden)
echo   3. User uploads blocklisted prohibited file-^> Terminated at Layer 4 in 7ms (403 Forbidden)
echo.
"%PYTHON_EXEC%" demo_college_mediator.py
echo.
pause
