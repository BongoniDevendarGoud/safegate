# SafeGate 2.0 — Capstone A1 Project Poster Specification

**Institution:** SR University, School of Computer Science & Artificial Intelligence  
**Candidate Name:** Bongoni Devendar Goud (Roll No: 2103A52001)  
**Project Title:** SafeGate 2.0: AI-Powered Website Video Upload Firewall & Frame-Level Deepfake Detection System  
**Poster HTML File:** `submission/poster_a1.html` (Formatted for standard ISO 216 A1: 594 mm × 841 mm)  

---

## 1. Print & Physical Specifications
- **Paper Size:** A1 Portrait (594 mm width × 841 mm height / 23.4 inches × 33.1 inches).
- **Paper Quality:** 200–250 GSM Glossy or Matte Executive Bond Paper.
- **Color Profile:** CMYK / RGB High Gamut (Resolution: $\ge 300\text{ DPI}$).
- **SRU University Logo:** Prominently featured on the upper right-hand corner as mandated by the University Guidelines.

---

## 2. Poster Visual Structure & Palette
- **Background:** Deep Cybersecurity Navy (`#070b14`).
- **Cards & Panes:** Slate Navy (`#0f172a`) with subtle cyan border glows (`#38bdf8`).
- **Primary Headers:** Electric Cyan (`#38bdf8`) & Crisp Pure White (`#ffffff`).
- **Classification Color Palette:**
  - 🟢 **GREEN (`#22c55e`):** Safe / Legitimate / Authentic Frame.
  - 🔴 **RED (`#ef4444`):** Morphed / Suspicious / AI-Manipulated / Bad Content.
  - 🟡 **YELLOW (`#eab308`):** Uncertain / Ambiguous Frame.

---

## 3. Section-by-Section Content Layout

### Header
- **University Ribbon:** SR UNIVERSITY &bull; SCHOOL OF COMPUTER SCIENCE AND ARTIFICIAL INTELLIGENCE &bull; CAPSTONE 2026-2027
- **Main Title:** SafeGate 2.0: AI-Powered Website Video Upload Firewall
- **Subtitle:** Complete Decoded Frame Extraction, Neural Deepfake Detection & Zero-Trust Publishing Gateway
- **Metadata:**
  - Student: Bongoni Devendar Goud (Roll No: 2103A52001)
  - Internal Guide: Dr. CH. Sandeep, Associate Professor & Head, School of CS&AI
  - Dean: Dr. M. Sheshikala, Professor & Dean, School of CS&AI
  - Coordinator: Mr. Sallauddin Md, Assistant Professor, School of CS&AI

### Column 1: Problem Statement & Protocol Stack
- **1. Problem Statement & Motivation:**
  - Weaponized generative AI video synthesis (Diffusion, GANs, face-swapping, sexual deepfakes).
  - Web Application Firewalls (WAFs) only examine network packets; video uploads remain uninspected binary payloads.
  - Subsampling vulnerability: 1-2 frames/second scanners miss single-frame temporal splice attacks.
- **2. Seven-Layer OSI Video Protocol Stack:**
  - Layer 1: Physical Bitstream Ingestion
  - Layer 2: Temporal Frame Link (Complete decoded extraction)
  - Layer 3: Transport & Hash Integrity (SHA-256 frame-level hashing)
  - Layer 4: Perceptual Identity Session (pHash visual blocklisting)
  - Layer 5: Forensic Presentation (Compression MSE & Laplacian variance)
  - Layer 6: Cognitive AI Application (PyTorch frequency classifier & Gemini fallback)
  - Layer 7: Firewall Policy Gate (ALLOW / QUARANTINE / BLOCK)

### Column 2: Ingestion Architecture & AI Detection Engine
- **3. In-Line Firewall Architecture & Any-App SDK:**
  - Direct proxy firewall between uploaders and the publishing backend (demonstrated live with an Instagram social platform interface).
  - Drop-in SDK for any application (Instagram, TikTok, Video KYC, News CMS) in 3 lines of code.
  - 100% extraction guarantee: 60-second 30 FPS video yields exactly 1,800 decoded frames without frame skipping.
  - Memory-efficient batch streaming via OpenCV & FFmpeg.
- **4. Strict Frame Color Classification Convention:**
  - 🟢 GREEN: Safe / Authentic CMOS optical camera capture.
  - 🔴 RED: Morphed / AI-manipulated / face-swap anomalies, high JPEG MSE.
  - 🟡 YELLOW: Inconclusive landmark certainty or underexposure.

### Column 3: Empirical Benchmark, SOC & Conclusion
- **5. Experimental Validation (6 Scenarios):**
  - Scenario 1 (Authentic): 100% GREEN -> ALLOW -> Published to Social Feed.
  - Scenario 2 (Deepfake): 45 RED -> QUARANTINE -> Blocked from public.
  - Scenario 3 (Single-Frame): Pinpoints Frame #25 at `00:00:01.042` as RED amid 44 GREEN frames.
  - Scenario 4 (Uncertain): Marked YELLOW -> QUARANTINE (Fail-closed).
  - Scenario 5 (Corrupted): Malformed bitstream -> BLOCK (Rejected).
  - Scenario 6 (Model Failure): Inference error -> QUARANTINE.
- **6. Tamper-Evident SHA-256 Audit Ledger & Verification:**
  - Immutable hash chain: $\text{Row}_i = \text{SHA256}(\text{Row}_{i-1} \parallel \text{Action} \parallel \text{UploadID} \parallel \text{Timestamp})$.
  - 74 out of 74 automated pytest unit and integration tests passing.
  - Zero-trust website gating guarantees unapproved videos never reach public users.

---

## 4. How to View and Print
Open `submission/poster_a1.html` in Chrome or Edge and press `Ctrl + P`. Set paper size to `A1` and background graphics to `On` to print directly to PDF or plotter.
