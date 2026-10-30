#!/usr/bin/env bash
# =====================================================================
# SafeGate — One-Click Runner (Linux / macOS)
# =====================================================================
set -e

if [ -d "venv" ]; then
    source venv/bin/activate
fi

export SAFEGATE_MOCK_MODEL=true

echo "====================================================================="
echo " SafeGate -- 7-Layer OSI Video Screening Gateway & CLI Appliance"
echo "====================================================================="
echo ""
echo "Select an option:"
echo " 1) Quick scan authentic clean video (sample_clean.mp4)"
echo " 2) Quick scan synthetic deepfake video (sample_malicious_deepfake.mp4)"
echo " 3) Verify cryptographic audit hash chain"
echo " 4) Launch headless screening server (http://localhost:8000)"
echo " 5) Run complete test suite (pytest)"
echo ""
read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        python cli.py scan samples/sample_clean.mp4
        ;;
    2)
        python cli.py scan samples/sample_malicious_deepfake.mp4
        ;;
    3)
        python cli.py audit
        ;;
    4)
        python cli.py serve
        ;;
    5)
        python -m pytest tests/ -v
        ;;
    *)
        echo "Invalid choice. Executing default scan on sample_clean.mp4..."
        python cli.py scan samples/sample_clean.mp4
        ;;
esac
