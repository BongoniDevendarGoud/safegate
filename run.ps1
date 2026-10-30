# SafeGate 7-Layer OSI Security Appliance (PowerShell)
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host " SafeGate -- 7-Layer OSI Security Screening Appliance & CLI" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

$defaultPython = "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe"
if (Test-Path $defaultPython) {
    $pythonExec = $defaultPython
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonExec = "python"
} else {
    Write-Error "Python executable not found. Please install Python 3.10+."
    exit 1
}

Set-Location $PSScriptRoot
$env:SAFEGATE_MOCK_MODEL = "true"

Write-Host "Executing 7-Layer OSI Stack scan on sample_clean.mp4..." -ForegroundColor Green
& $pythonExec cli.py scan sample_clean.mp4
