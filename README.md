# SafeGate — Self-Hosted 7-Layer OSI Video Security & Deepfake Screening Gateway

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![OSI Model](https://img.shields.io/badge/Architecture-7--Layer%20OSI%20Stack-orange.svg)]()
[![Tests](https://img.shields.io/badge/Tests-60%20Passed%20(100%25)-brightgreen.svg)]()
[![Security](https://img.shields.io/badge/Design-Fail--Closed%20%26%20Tamper--Resistant-critical.svg)]()
[![Docker](https://img.shields.io/badge/Docker-Multi--Stage%20Hardened-blue.svg)](Dockerfile)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

SafeGate is a self-hosted, **fail-closed AI security screening gateway and CLI appliance** that inspects video uploads for prohibited explicit content and synthetic deepfake manipulation **before** media is published.

Engineered with a **7-Layer OSI Protocol Stack**, SafeGate enforces strict defense-in-depth across the physical bitstream, temporal frame link, transport integrity, perceptual hashes, and cognitive AI vision models.

---

## Key Features

- **7-Layer OSI Protocol Stack:** Every incoming video is screened sequentially from Layer 1 (Physical Bitstream Ingestion) through Layer 7 (Cognitive AI Policy Gate).
- **Synthetic Deepfake Detection:** Multi-signal forensic heuristics evaluate temporal sharpness variance (CoV), consecutive color histogram discontinuity, compression residuals (MSE), and container metadata.
- **Fail-Closed Architecture:** Network timeouts, corrupted frames, missing API credentials, or ambiguous classifications always route media to `REVIEW` or `BLOCK`—never failing open to `ALLOW`.
- **Zero Retention of Blocked Media:** Prohibited files are destroyed immediately from disk upon detection. Only non-reversible cryptographic checksums (SHA-256) and perceptual fingerprints (pHash) are retained.
- **Tamper-Evident SHA-256 Audit Trail:** Every decision, administrative action, and appeal is cryptographically chained using HMAC SHA-256 into an immutable sequential ledger.
- **Unified Interfaces:** Operates both as a high-speed Command-Line Interface (`cli.py`) and a headless REST API with a responsive web moderation dashboard (`dashboard/`).
- **Offline & Cloud Hybrid:** Fully operational offline out of the box using local models (`Falconsai/nsfw_image_detection`), with optional Google Gemini 2.5 Flash second-opinion review for borderline cases.

---

## 60-Second Quickstart

### Prerequisites
- Python 3.10+ (Tested up to Python 3.14)
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/safegate.git
cd safegate
```

### 2. Automated One-Click Setup

**On Windows:**
```cmd
setup.bat
```

**On Linux / macOS:**
```bash
chmod +x setup.sh run.sh
./setup.sh
```

*(Alternatively, create a virtual environment manually:)*
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
python generate_test_samples.py
```

---

## Running SafeGate

### Quick Scans via CLI Appliance

SafeGate includes pre-generated synthetic test samples in the `samples/` directory so you can test immediately:

#### 1. Scan an Authentic / Normal Video
```bash
python cli.py scan samples/sample_clean.mp4
```
**Output:**
```text
Initiating OSI Protocol Stack Analysis on: sample_clean.mp4
Size: 55,215 bytes | Client IP: 127.0.0.1

LAYER        SUBSYSTEM                        STATUS     LATENCY    DETAILS
-------------------------------------------------------------------------------------
Layer 5      Session (Authentication)         PASS          0.0ms  Session authenticated.
Layer 3      Network (Traffic Policing)       PASS          0.0ms  Traffic conforms to policy.
Layer 1      Physical (Bitstream Ingestion)   PASS          0.5ms  Stream buffered safely.
Layer 6      Presentation (Syntax Validation) PASS          1.4ms  MIME confirmed: video/mp4
Layer 4      Transport (Integrity & Match)    PASS          7.5ms  SHA-256 clean.
Layer 2      Data Link (Temporal Framing)     PASS         34.5ms  Extracted 3 synchronized frames.
Layer 6      Presentation (pHash Dedup)       PASS        436.3ms  Blocklist clean.
Layer 7      Application (Cognitive Policy)   ALLOW        60.1ms  NSFW: 0.02, Deepfake: 10/100 -> ALLOW
-------------------------------------------------------------------------------------

>>> FINAL VERDICT: ALLOW (Published) <<<
Deepfake Risk:   10/100 (Safe, Authentic Media)
Action Taken:    Media cleared all security stages and transferred to /published/
```

#### 2. Scan a Synthetic Deepfake Video
```bash
python cli.py scan samples/sample_malicious_deepfake.mp4
```
**Output:**
```text
Initiating OSI Protocol Stack Analysis on: sample_malicious_deepfake.mp4
Size: 1,187,899 bytes | Client IP: 127.0.0.1

LAYER        SUBSYSTEM                        STATUS     LATENCY    DETAILS
-------------------------------------------------------------------------------------
...
Layer 7      Application (Cognitive Policy)   REVIEW       74.7ms  NSFW: 0.02, Deepfake: 75/100 -> REVIEW
-------------------------------------------------------------------------------------

>>> FINAL VERDICT: REVIEW (Quarantined) <<<
Deepfake Risk:   75/100 (Exceeds review threshold of 60)
Advisory Signals: Boundary sharpness variance (CoV: 0.71); Temporal color discontinuity (-0.05); Compression noise (MSE: 53.8); Missing camera hardware metadata.
Action Taken:    Media routed to secure /quarantine/ vault for human moderator review.
```

#### 3. Verify Cryptographic Audit Chain Integrity
```bash
python cli.py audit
```
**Output:**
```text
Verifying Cryptographic SHA-256 Audit Hash Chain...
-----------------------------------------------------------------
✓ AUDIT INTEGRITY: VALID (Cryptographic Chain Intact)
Total Sequential Records: 23
Broken at Row ID:         None (Zero tampering detected)
Verification Summary:     Audit chain verified: all entries cryptographically intact.
-----------------------------------------------------------------
```

#### 4. Launch Headless Server Daemon & Web Dashboard
```bash
python cli.py serve
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser to access the live web moderation dashboard.

---

## 7-Layer OSI Protocol Stack Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                   7-LAYER OSI SECURITY STACK                           │
├─────────┬───────────────────────────┬──────────────────────────────────┤
│ Layer   │ Subsystem Name            │ Security Enforcement Mechanism   │
├─────────┼───────────────────────────┼──────────────────────────────────┤
│ Layer 7 │ Application Cognitive Gate│ Local ViT, Gemini AI, Deepfake   │
│ Layer 6 │ Presentation Formatting   │ Magic bytes MIME & 64-bit pHash  │
│ Layer 5 │ Session Authentication    │ HMAC constant-time auth & chain  │
│ Layer 4 │ Transport Integrity       │ SHA-256 exact-match blocklist    │
│ Layer 3 │ Network Traffic Policing  │ Sliding-window IP rate limiter   │
│ Layer 2 │ Data Link Framing         │ OpenCV temporal frame sampling   │
│ Layer 1 │ Physical Bitstream        │ Hard 200MB quota & chunk bounds  │
└─────────┴───────────────────────────┴──────────────────────────────────┘
```

1. **Layer 1: Physical (Bitstream Ingestion):** Buffers the raw byte stream in isolated quarantine memory, strictly enforcing a 200MB hard quota before parsing.
2. **Layer 2: Data Link (Temporal Framing):** Decodes video streams into synchronized temporal frames at bounded intervals ($1\text{ frame }/\, 2\text{s}$, capped at 60 frames max) preventing decompression bombs.
3. **Layer 3: Network (Traffic Policing):** Sliding-window rate limiter restricting IP addresses to $\le 10\text{ uploads }/\, \text{min}$.
4. **Layer 4: Transport (Integrity & Blocklist):** Computes cryptographic SHA-256 checksums in constant time. If the hash matches the known blocklist, processing halts in $<10\text{ms}$ with an immediate `BLOCK`.
5. **Layer 5: Session (Cryptographic Identity):** Verifies API keys using constant-time comparisons (`hmac.compare_digest`) and logs events to an immutable SHA-256 hash chain.
6. **Layer 6: Presentation (Syntax & pHash):** Validates MIME magic bytes (`video/mp4`, `video/webm`, `video/quicktime`) and computes 64-bit Discrete Cosine Transform perceptual hashes (pHash) to catch re-encoded duplicate media (Hamming distance $\le 10$).
7. **Layer 7: Application (Cognitive Policy Gate):** Multi-model AI analysis:
   - **Local Vision Transformer:** Offline explicit content classifier (`Falconsai/nsfw_image_detection`).
   - **Cloud Second Opinion:** Google Gemini 2.5 Flash triggered strictly for borderline scores ($[0.45, 0.85)$).
   - **Deepfake Forensic Scorer:** Evaluates subject boundary sharpness variance ($\text{CoV} \ge 0.70$), color histogram shifts ($\le 0.40$), and compression residual noise.

---

## Deepfake Detection Signals

SafeGate evaluates four independent forensic indicators to compute a composite manipulation probability ($0 - 100$):

$$\text{Deepfake Risk} = w_1 \cdot S_{\text{sharpness}} + w_2 \cdot S_{\text{color}} + w_3 \cdot S_{\text{compression}} + w_4 \cdot S_{\text{metadata}}$$

- **Signal 1: Temporal Sharpness Instability (CoV):** AI face-swaps and synthetic frame generators suffer from temporal jitter across subject boundaries. SafeGate measures the Coefficient of Variation ($\text{CoV} = \sigma / \mu$) of Laplacian variance across frames.
- **Signal 2: Color Histogram Continuity:** Detects unnatural color shifts between consecutive frames using normalized Bhattacharyya/correlation distance.
- **Signal 3: Compression Residuals (MSE):** Analyzes high-frequency residual differences between raw and re-quantized frames.
- **Signal 4: Hardware EXIF & Container Tags:** Inspects the media container for natural camera manufacturer tags vs. synthetic rendering signatures.

Any video scoring $\ge 60$ triggers an automatic **`REVIEW`** quarantine.

---

## CLI Command Reference

| Command | Description | Example |
|---|---|---|
| `scan <file>` | Runs file through all 7 OSI Layers | `python cli.py scan video.mp4` |
| `audit` | Verifies cryptographic audit hash chain | `python cli.py audit` |
| `stats` | Displays total counts (ALLOW, REVIEW, BLOCK) | `python cli.py stats` |
| `blocklist` | Queries or adds hashes to transport blocklist | `python cli.py blocklist --add <sha256>` |
| `serve` | Launches HTTP server on `http://0.0.0.0:8000` | `python cli.py serve` |

---

## Docker Deployment

SafeGate includes a hardened, multi-stage production `Dockerfile` running as a non-root user (`uid 10001`):

```bash
# Build and run with Docker Compose
docker compose up --build

# Run a test scan inside the container
docker exec -it safegate-gateway python cli.py scan samples/sample_clean.mp4
```

---

## Automated Test Suite

SafeGate features a 60-test comprehensive test suite verifying all 7 layers, edge cases, fail-closed handlers, cryptographic tampering detection, and deepfake heuristics:

```bash
python -m pytest tests/ -v
```

**Result:**
```text
======================== 60 passed, 1 warning in 3.47s ========================
```

---

## Project Structure

```
safegate/
├── app/
│   ├── main.py                     # FastAPI server daemon & security middleware
│   ├── config.py                   # Central configuration & policy thresholds
│   ├── db.py                       # SQLAlchemy SQLite engine & session management
│   ├── osi/                        # 7-Layer OSI Implementation
│   │   ├── layer1_physical.py      # Layer 1: Bitstream buffer & 200MB quota
│   │   ├── layer2_datalink.py      # Layer 2: Temporal video framing
│   │   ├── layer3_network.py       # Layer 3: Sliding window IP rate limiter
│   │   ├── layer4_transport.py     # Layer 4: SHA-256 integrity & blocklist
│   │   ├── layer5_session.py       # Layer 5: Constant-time auth & hash chain
│   │   ├── layer6_presentation.py  # Layer 6: MIME syntax & pHash deduplication
│   │   ├── layer7_application.py   # Layer 7: AI Vision & Deepfake Heuristics
│   │   └── stack.py                # OSI Protocol Stack Coordinator
│   ├── models/database.py          # ORM models (Upload, AuditLog, Blocklists)
│   ├── routes/                     # REST API endpoints
│   └── security/                   # Security headers, CORS, rate limiting
├── dashboard/                      # Single-page web moderation dashboard
├── samples/                        # Authentic and deepfake test videos
├── tests/                          # 60 automated unit and integration tests
├── .env.example                    # Environment configuration template
├── cli.py                          # Unified CLI appliance
├── Dockerfile                      # Hardened container definition
├── docker-compose.yml              # Multi-container orchestration
├── setup.bat / setup.sh            # One-click environment setup
└── run.bat / run.sh                # One-click interactive launcher
```

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
