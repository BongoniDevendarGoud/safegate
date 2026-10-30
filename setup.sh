#!/usr/bin/env bash
# =====================================================================
# SafeGate — One-Click Setup Script (Linux / macOS)
# =====================================================================
set -e

echo "====================================================================="
echo "   SafeGate -- One-Click Setup & Dependency Installation"
echo "====================================================================="
echo ""

# Check Python
if command -v python3 &>/dev/null; then
    PY_BIN="python3"
elif command -v python &>/dev/null; then
    PY_BIN="python"
else
    echo "[ERROR] Python 3.10+ is required but was not found on PATH."
    exit 1
fi

echo "[*] Using Python: $($PY_BIN --version)"

# Create venv if not present
if [ ! -d "venv" ]; then
    echo "[*] Creating virtual environment (venv)..."
    $PY_BIN -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install requirements
echo "[*] Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env from template if missing
if [ ! -f ".env" ]; then
    echo "[*] Generating default .env from .env.example..."
    cp .env.example .env
fi

# Generate test samples if missing
if [ ! -f "samples/sample_clean.mp4" ]; then
    echo "[*] Generating synthetic test media samples..."
    python generate_test_samples.py
    mkdir -p samples
    cp -n sample_clean.mp4 samples/ 2>/dev/null || true
    cp -n sample_malicious_deepfake.mp4 samples/ 2>/dev/null || true
fi

echo ""
echo "====================================================================="
echo " [SUCCESS] SafeGate is installed and ready for live execution!"
echo "====================================================================="
echo ""
echo "Test scan:"
echo "   python cli.py scan samples/sample_clean.mp4"
echo "   python cli.py scan samples/sample_malicious_deepfake.mp4"
echo ""
echo "Or start server daemon:"
echo "   python cli.py serve"
echo ""
