# SafeGate Global Internet Mediator Prototype Demo (PowerShell)
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host " SafeGate -- Global Internet Upload Mediator (College Prototype)" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

$pythonExec = "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe"
if (-not (Test-Path $pythonExec)) {
    $pythonExec = "python"
}

Set-Location $PSScriptRoot
& $pythonExec demo_college_mediator.py
