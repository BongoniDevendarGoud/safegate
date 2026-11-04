# SafeGate 2.0 — AI-Powered Website Video Upload Firewall & Frame-Level Deepfake Detection System

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C.svg)](https://pytorch.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-FFmpeg%20Decoded-5C3EE8.svg)](https://opencv.org/)
[![Tests](https://img.shields.io/badge/Tests-74%20Passed%20(100%25)-brightgreen.svg)]()
[![Security](https://img.shields.io/badge/Architecture-Fail--Closed%20%7C%20Zero--Trust-critical.svg)]()
[![Docker](https://img.shields.io/badge/Docker-Multi--Stage%20Hardened-blue.svg)](Dockerfile)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**SafeGate 2.0** is an enterprise-grade cybersecurity video upload firewall and frame-level deepfake detection system. Designed to sit directly between public uploaders and website publishing backends (e.g. YouTube, TikTok, or Instagram clones), SafeGate intercepts every incoming video, buffers it into isolated quarantine, extracts **every single decoded frame** without downsampling, and runs neural AI and forensic analysis before making an authoritative **ALLOW**, **QUARANTINE**, or **BLOCK** determination.

> [!IMPORTANT]
> **Strict Zero-Trust Publishing Rule:** A video is **never** published to the public website feed until it has fully cleared SafeGate's frame-by-frame verification. Quarantined or rejected videos are strictly inaccessible to public users.

---

## 1. System Architecture

```text
       USER UPLOADS VIDEO
               |
               v
  DEMO VIDEO-SHARING WEBSITE (SafeTube)
               |
               v [INTERCEPTED]
    SAFEGATE UPLOAD FIREWALL
               |
               v
  STAGE 1: FILE VALIDATION & SECURE BUFFERING (Magic Bytes, Non-Executable Quarantine)
               |
               v
  STAGE 2: VIDEO METADATA EXTRACTION (Duration, Container, FPS, Dimensions)
               |
               v
  STAGE 3: COMPLETE FRAME EXTRACTION (FFmpeg / OpenCV, Every Decoded Frame, SHA-256)
               |
               v
  STAGE 4: FRAME-BY-FRAME AI & FORENSIC DETECTION (PyTorch CNN + Forensic Engine)
               |
               v
  STAGE 5: FRAME COLOR CLASSIFICATION (RED = Legit, GREEN = Suspicious, YELLOW = Uncertain)
               |
               v
  STAGE 6: VIDEO RISK ASSESSMENT (Composite Risk Scoring 0 - 100)
               |
               v
  STAGE 7: FIREWALL POLICY DECISION ENGINE
               |
      +--------+-----------------------+
      |                                |                               |
      v                                v                               v
    ALLOW                          QUARANTINE                        BLOCK
(All Frames RED)              (>=1 GREEN / YELLOW)             (Corrupted / Prohibited)
      |                                |                               |
      v                                v                               v
PUBLISH TO WEBSITE               SOC ADMIN REVIEW                REJECT & PURGE
```

---

## 2. Complete Frame Extraction Engine

Unlike superficial tools that only sample 1 or 2 frames per second, **SafeGate 2.0 decodes and extracts every individual frame** using OpenCV and FFmpeg:

- **100% Extraction Guarantee:** A 60-second video at 30 FPS yields **exactly 1,800 decoded frames**. For a 10-minute video, all 18,000 frames are processed sequentially in stream batches.
- **Cryptographic Fingerprinting:** Every extracted frame is hashed with **SHA-256** and stamped with its exact index and millisecond timestamp (`HH:MM:SS.mmm`).
- **Progress Tracking & Accounting:** Telemetry continuously tracks total expected frames, successfully extracted frames, classified frames, and failed frames.
- **Fail-Closed Integrity:** If decoding aborts or frames cannot be classified, the video is **never allowed** and routes immediately to `QUARANTINE` or `BLOCK`.

---

## 3. Modular AI & Forensic Detection Engine

SafeGate 2.0 combines deep neural networks with physical optical heuristics to detect AI manipulation:

1. **PyTorch Deepfake Classifier:** Convolutional frequency-domain neural model analyzing spatial high-frequency artifacts, GAN grid patterns, and neural blending seams.
2. **Compression Residual Error (MSE):** Measures double-compression error residuals to identify face-swapping splice boundaries.
3. **Laplacian Edge Sharpness:** Evaluates focus consistency and natural optical camera dispersion across frames.
4. **Temporal Color Correlation:** Tracks inter-frame histogram coherence to catch sudden deepfake frame flicker or illumination jumps.
5. **Fail-Closed Fallback:** If an AI model becomes unavailable or encounters an unhandled inference exception, SafeGate records the failure and forces a **QUARANTINE** verdict.

---

## 4. Strict Frame Color Classification System

SafeGate 2.0 employs a strict, user-specified color convention:

| Classification | Visual Marker | Hex Code | Meaning & System Response |
| :--- | :---: | :---: | :--- |
| **LEGITIMATE** | 🔴 **RED** | `#ef4444` | **Authentic frame.** Captured naturally by physical CMOS optical sensor. Natural noise and color coherence. |
| **SUSPICIOUS / AI** | 🟢 **GREEN** | `#22c55e` | **AI-Manipulated / Deepfake.** Neural synthesis artifacts, face-swapping anomalies, or splice boundaries detected. |
| **UNCERTAIN** | 🟡 **YELLOW** | `#eab308` | **Ambiguous / Inconclusive.** Low Laplacian variance, extreme underexposure, or model inference uncertainty. |

> [!WARNING]
> **Intentional Inversion:** SafeGate's RED (Legitimate) and GREEN (Suspicious) convention is intentionally distinct from conventional consumer dashboards by design. Do not alter this mapping.

---

## 5. Interactive Web Application

The frontend dashboard provides 7 dedicated security views:

1. **Demo Video-Sharing Platform ("SafeTube"):** Real-world platform simulation (similar to YouTube/Instagram). Displays only videos that have cleared the firewall with an `ALLOW` decision. Quarantined media remains hidden.
2. **Video Upload & Intercept:** Dropzone interface allowing users to upload MP4, MOV, AVI, or WebM media with real-time video stream preview and pre-flight metadata extraction.
3. **Real-Time Firewall Scanner:** Live visualization of the 8-stage pipeline, real-time extraction progress bar, SSE event telemetry, and policy determination.
4. **Interactive Frame Inspection Gallery:** Grid view of all extracted frames with filter chips (`All`, `🔴 Legitimate`, `🟢 Suspicious / AI`, `🟡 Uncertain`). Clicking any card opens the deep frame inspection modal with high-res display and adjacent frame comparison.
5. **Video Frame Timeline:** Interactive temporal scrubber mapping colored markers (RED, GREEN, YELLOW) across the entire video runtime. Automatically clusters consecutive suspicious frames into **Suspicious Segments** (e.g., `Frames 25–25 (00:00:01.041 - 00:00:01.083)`).
6. **SOC Moderation Dashboard:** Security Operations Center console featuring Chart.js telemetry graphs, the active quarantine review queue, one-click manual `Approve` and `Reject` actions, and the tamper-evident SHA-256 audit ledger.
7. **Video Security Report:** Formal cryptographic verification certificate including media fingerprints, frame breakdown, AI telemetry, and one-click JSON download or PDF export.

---

## 6. One-Click Demonstration Scenarios (Mentor Evaluation Guide)

SafeGate 2.0 includes 5 real generated MP4 test videos located in `samples/` and a persistent top-bar scenario launcher (`scen-1` through `scen-6`) to demonstrate all required capabilities in seconds:

### Scenario 1: Authentic Video Upload (Passes Firewall)
- **Input:** `samples/scenario1_legitimate.mp4` (natural camera gradients and realistic kinematics).
- **Execution:** Click button **`1 Authentic Video (ALLOW)`** or run `python cli.py scan samples/scenario1_legitimate.mp4`.
- **Expected Outcome:**
  - All 45 frames classified as **Legitimate** and marked **RED**.
  - Risk Score: `0 / 100`.
  - Firewall Decision: **ALLOW**.
  - Public Feed: Video is immediately published and playable on the **Demo Video Platform**.

### Scenario 2: Deepfake Video Upload (Intercepted & Quarantined)
- **Input:** `samples/scenario2_deepfake.mp4` (synthetic high-frequency flicker and high JPEG residual error).
- **Execution:** Click button **`2 Deepfake Video (QUARANTINE)`**.
- **Expected Outcome:**
  - Frames flagged as **Suspicious / AI-Manipulated** and marked **GREEN**.
  - Risk Score: `>= 80 / 100`.
  - Firewall Decision: **QUARANTINE**.
  - Public Feed: Video is **blocked from publication**.
  - SOC Dashboard: Added to the Quarantine Review Queue with review actions.

### Scenario 3: Single-Frame Modification Detection (Temporal Discontinuity)
- **Input:** `samples/scenario3_single_modified.mp4` (45-frame video where exactly **Frame #25** has injected synthetic artifacts, while all other 44 frames are pristine).
- **Execution:** Click button **`3 Single-Frame Tamper (QUARANTINE)`**.
- **Expected Outcome:**
  - Exact frame identified: **Frame #25** at timestamp `00:00:01.042` marked **GREEN**.
  - All 44 surrounding frames marked **RED**.
  - Timeline: Identifies suspicious segment at Frame 25.
  - Frame Gallery: Side-by-side comparison displays clean Frame #24 (RED) vs tampered Frame #25 (GREEN) vs clean Frame #26 (RED).
  - Firewall Decision: **QUARANTINE**.

### Scenario 4: Uncertain Frame Handling (Fail-Closed)
- **Input:** `samples/scenario4_uncertain.mp4` (flat ambiguous low-contrast bitstream with low Laplacian variance).
- **Execution:** Click button **`4 Uncertain Clarity (YELLOW)`**.
- **Expected Outcome:**
  - Frames marked **YELLOW** (Uncertain).
  - Risk Score elevated to Moderate (`50 / 100`).
  - Firewall Decision: **QUARANTINE** (demonstrating fail-closed zero-trust policy).

### Scenario 5: Corrupted / Malformed Stream (Rejection & Blocking)
- **Input:** `samples/scenario5_corrupted.mp4` (malformed bitstream with broken header/index).
- **Execution:** Click button **`5 Corrupted Stream (BLOCK)`**.
- **Expected Outcome:**
  - Intake validator detects invalid container headers.
  - Firewall Decision: **BLOCK**.
  - File is rejected and immediately purged from disk.

### Scenario 6: AI Model Failure (Fail-Closed Architecture)
- **Input:** Programmatic simulation of neural inference exception.
- **Execution:** Click button **`6 Model Failure (FAIL-CLOSED)`**.
- **Expected Outcome:**
  - Model status transitions to `INFERENCE_FAILURE`.
  - Fail-closed rule triggers: SafeGate **refuses to fail open**.
  - Firewall Decision: **QUARANTINE**.

---

## 7. Installation & Quickstart

### Prerequisites
- Python 3.10+ (Tested on Python 3.10, 3.11, 3.12, 3.14)
- Git & FFmpeg

### Step 1: Clone Repository & Create Virtual Environment
```bash
git clone https://github.com/BongoniDevendarGoud/safegate.git
cd safegate

# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Generate Demonstration Test Samples
```bash
python generate_demonstration_videos.py
```
*Creates all 5 scenario video streams in `samples/`.*

### Step 4: Start SafeGate 2.0 Web Platform
```bash
# Windows
start_website.bat

# Or direct command on any OS:
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Open your browser at **`http://localhost:8000`**.

---

## 8. Automated Test Suite

SafeGate 2.0 maintains a comprehensive automated testing suite covering all 7 OSI layers, AI frame extraction, and the 6 firewall scenarios:

```bash
pytest -v
```

### Test Suite Execution Output
```text
======================================= test session starts =======================================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
collected 74 items

tests/test_safegate2.py ...............                                                    [ 20%]
tests/test_audit.py ......                                                                 [ 28%]
tests/test_cli.py ......                                                                   [ 36%]
tests/test_decision.py .........                                                           [ 48%]
tests/test_hashing.py .....                                                                [ 55%]
tests/test_intake.py ......                                                                [ 63%]
tests/test_moderation.py .......                                                           [ 72%]
tests/test_network.py ......                                                               [ 81%]
tests/test_pipeline.py ........                                                            [ 91%]
tests/test_presentation.py ......                                                          [100%]

======================================= 74 passed in 7.82s =======================================
```

---

## 9. REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/videos/upload` | Ingest video file, compute SHA-256, buffer into quarantine |
| `POST` | `/api/videos/{id}/scan` | Execute 8-stage frame extraction, AI inference, and risk assessment |
| `GET` | `/api/videos/{id}/status` | Retrieve scan status and frame statistics |
| `GET` | `/api/videos/{id}/events` | Server-Sent Events (SSE) real-time scanning progress stream |
| `GET` | `/api/videos/{id}/frames` | Paginated list of extracted frames with classifications and markers |
| `GET` | `/api/videos/{id}/frames/{f_id}` | Full frame details with adjacent previous and next frame links |
| `GET` | `/api/videos/{id}/frames/{f_id}/image` | High-resolution frame PNG/JPEG image |
| `GET` | `/api/videos/{id}/frames/{f_id}/thumbnail` | Stamped thumbnail with color-coded classification badge |
| `GET` | `/api/videos/{id}/timeline` | Colored timeline ticks and grouped suspicious segments |
| `GET` | `/api/videos/{id}/report` | Cryptographic JSON security verification certificate |
| `GET` | `/api/website/videos` | Public website media feed (only returns `ALLOW` / `published` videos) |
| `GET` | `/api/website/videos/{id}/stream` | Public video streaming endpoint (gates quarantined videos) |
| `GET` | `/api/admin/dashboard` | SOC dashboard metrics, decisions summary, and audit ledger |
| `POST` | `/api/admin/videos/{id}/approve` | SOC administrator approval override (publishes video) |
| `POST` | `/api/admin/videos/{id}/reject` | SOC administrator rejection (purges video) |
| `POST` | `/api/demo/run-scenario/{id}` | Instant trigger for demonstration scenarios 1 through 6 |

---

## 10. Docker Deployment

Deploy SafeGate 2.0 as an isolated, non-root microservice using Docker:

```bash
# Build and run with Docker Compose
docker-compose up --build -d

# Check health check
docker-compose ps
```

---

## 11. Security Audit & Cryptographic Ledger

SafeGate implements an immutable SHA-256 HMAC hash-chained audit ledger. Every upload, scan result, moderator determination, and automated decision writes a block to the database:

$$\text{RowHash}_i = \text{SHA256}(\text{RowHash}_{i-1} \parallel \text{UploadID} \parallel \text{Action} \parallel \text{Timestamp})$$

Clicking **"Verify Hash Chain Integrity"** on the SOC Moderation Dashboard traverses the entire database to ensure zero tampering, deleted rows, or retroactively modified decisions.

---

## 12. License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
