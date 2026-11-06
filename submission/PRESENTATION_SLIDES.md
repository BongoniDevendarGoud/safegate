# SafeGate 2.0 — Capstone Presentation Slides & Speaker Guide

**Institution:** SR University, School of Computer Science & Artificial Intelligence  
**Candidate Name:** Bongoni Devendar Goud (Roll No: 2103A52001)  
**Project Title:** SafeGate 2.0: AI-Powered Website Video Upload Firewall & Frame-Level Deepfake Detection System  
**Presentation File:** `submission/2103A52001-Bongoni_Devendar_Goud_Presentation.pptx` (16 Slides)  

---

### Slide 1: Title Slide (Cover & Metadata)
- **Header Category:** CAPSTONE PROJECT PRESENTATION | ACADEMIC YEAR 2026-2027
- **Main Title:** SafeGate 2.0: AI-Powered Website Video Upload Firewall
- **Subtitle:** Frame-Level Deepfake Detection & In-Line Content Verification Gateway
- **Content:**
  - Candidate: Bongoni Devendar Goud (Roll No: 2103A52001)
  - Degree: Bachelor of Technology, School of Computer Science & Artificial Intelligence
  - University: SR University, Ananthsagar, Warangal, Telangana - 506371
  - Internal Guide: Dr. CH. Sandeep, Associate Professor & Head, School of CS&AI
  - Dean: Dr. M. Sheshikala, Professor & Dean, School of CS&AI
  - Project Coordinator: Mr. Sallauddin Md, Assistant Professor, School of CS&AI
- **Speaker Notes:** "Good morning respected reviewers and panel members. Today I am presenting my Capstone Project, SafeGate 2.0, an in-line AI video firewall and frame-level deepfake detection system built to protect social media and video-sharing platforms."

---

### Slide 2: Problem Definition & Motivation
- **Header Category:** PROBLEM DEFINITION & MOTIVATION
- **Title:** The Threat Landscape: Deepfakes in Web Applications
- **Subtitle:** Why Traditional Web Application Firewalls (WAFs) Fail
- **Content:**
  - Proliferation of Synthetic Media: Generative AI tools allow instantaneous digital forgery.
  - Perimeter Blindspot: Standard WAFs (Cloudflare, AWS) inspect HTTP packets and SQL/XSS signatures, treating video uploads as black-box blobs.
  - Irreversible Damage Post-Publication: Once unverified video reaches the CDN, reputational harm occurs in seconds.
  - Subsampling Vulnerability: Existing scanners sample only 1-2 frames/second, allowing single-frame splice attacks to bypass detection.
  - Core Objective: Build an in-line upload firewall that intercepts uploads, decodes every frame, and enforces zero-trust gating.
- **Speaker Notes:** "Current web security tools have a fatal blindspot: they treat video files as opaque payloads. If an attacker injects a deepfake face or even a single modified frame, standard firewalls pass it through directly to the publishing datastore."

---

### Slide 3: High-Level System Architecture
- **Header Category:** SYSTEM ARCHITECTURE
- **Title:** SafeGate 2.0: High-Level Ingestion Firewall Flow
- **Subtitle:** Zero-Trust Mediation Between Uploaders and Publishing Backend
- **Content:**
  - In-line interception buffer before publication.
  - 8-stage verification pipeline: File validation, metadata, complete frame extraction, AI detection, forensic heuristics, color marking, risk scoring, and policy enforcement.
  - 3-tier policy outcome: ALLOW, QUARANTINE, BLOCK.
- **Speaker Notes:** "SafeGate 2.0 operates as an active proxy firewall. The demo video-sharing website (SafeTube) cannot publish any video until SafeGate outputs an explicit ALLOW decision."

---

### Slide 4: Seven-Layer OSI Video Security Protocol
- **Header Category:** THEORETICAL FOUNDATION
- **Title:** Seven-Layer Defense-in-Depth Protocol Stack
- **Subtitle:** Comprehensive Physical to Cognitive Verification Pipeline
- **Content:**
  - Layer 1: Physical Bitstream Ingestion (Magic bytes, non-executable isolation).
  - Layer 2: Temporal Frame Link (Complete decoded frame extraction via OpenCV/FFmpeg).
  - Layer 3: Transport & Hash Integrity (SHA-256 frame-level hashing).
  - Layer 4: Perceptual Identity Session (pHash visual blocklisting).
  - Layer 5: Forensic Presentation (Compression residuals, Laplacian variance, color correlation).
  - Layer 6: Cognitive AI Application (PyTorch frequency classifier & Gemini fallback).
  - Layer 7: Firewall Policy Gate (Automated tri-state decisioning).
- **Speaker Notes:** "Our architecture preserves the 7-layer defense-in-depth model inspired by the OSI stack, extending from raw binary bitstreams up to cognitive deepfake neural classification."

---

### Slide 5: 100% Decoded Frame Extraction Guarantee
- **Header Category:** CORE INNOVATION #1
- **Title:** Complete Decoded Frame Extraction Engine
- **Subtitle:** Zero Subsampling: Eliminating Temporal Splice Blindspots
- **Content:**
  - A 60-second video at 30 FPS yields exactly 1,800 decoded frames.
  - OpenCV/FFmpeg stream decompression without out-of-memory overhead.
  - Every extracted frame receives an independent SHA-256 hash and millisecond timestamp.
  - Accounting checks ensure extracted_frames == total_decoded_frames before permitting approval.
- **Speaker Notes:** "This is one of our primary innovations. We do not merely inspect a couple of keyframes. We decode and extract every individual frame, calculating cryptographic fingerprints for each."

---

### Slide 6: Dual-Engine AI Frame Classification
- **Header Category:** CORE INNOVATION #2
- **Title:** Dual-Engine AI Frame Classification
- **Subtitle:** Combining Neural Frequency Artifacts with Optical Physics
- **Content:**
  - PyTorch Frequency Convolutional Network detecting high-frequency generative artifacts.
  - Compression Residual Error (MSE) detecting re-compression seams.
  - Laplacian Edge Variance evaluating focus and sensor dispersion.
  - Inter-Frame Color Correlation tracking temporal color shifts.
  - Fail-closed error isolation: Unhandled model exceptions force QUARANTINE.
- **Speaker Notes:** "A single model cannot catch every deepfake. We use a dual-engine paradigm: a PyTorch deep learning convolutional neural network paired with physical forensic heuristics."

---

### Slide 7: Strict Frame Color Classification Convention
- **Header Category:** STANDARDS & CONVENTIONS
- **Title:** Frame Color Classification Convention
- **Subtitle:** Strict Forensic Mapping for Video Security
- **Content:**
  - 🟢 GREEN: Safe / Authentic Frame (Natural CMOS sensor noise, pristine edge sharpness, legitimate).
  - 🔴 RED: Morphed / Suspicious / Bad Content (Deepfake facial artifacts, high compression residuals, sexual/harmful media).
  - 🟡 YELLOW: Uncertain Frame (Underexposed frames, ambiguous landmark confidence).
  - Visual frame stamping applies colored borders and uppercase badges.
- **Speaker Notes:** "We follow the industry-standard visual convention: GREEN represents Safe/Authentic videos, RED represents Morphed, deepfake or bad content, and YELLOW represents Uncertain frames."

---

### Slide 8: Composite Video Risk Assessment & Policy
- **Header Category:** DECISION ENGINE
- **Title:** Composite Video Risk Assessment & Policy
- **Subtitle:** Mathematically Rigorous 0 to 100 Scoring Model
- **Content:**
  - $\text{Risk Score} = \min(100, (\text{Suspicious\_Ratio} \times 85) + (\text{Uncertain\_Ratio} \times 35) + \text{Max\_Anomaly} \times 20)$
  - ALLOW: 100% GREEN frames -> Published to feed.
  - QUARANTINE: $\ge 1$ RED or YELLOW frame -> Isolated for SOC review.
  - BLOCK: Prohibited checksum or malformed bitstream -> Rejected & purged.
- **Speaker Notes:** "Our composite risk engine combines ratios of suspicious and uncertain frames with peak anomaly scores. Even a single tampered frame immediately locks the video in quarantine."

---

### Slide 9: Demo Video-Sharing Platform Simulation
- **Header Category:** FULL-STACK IMPLEMENTATION
- **Title:** Demo Video-Sharing Platform Simulation
- **Subtitle:** Simulating YouTube / Instagram Ingestion Protection
- **Content:**
  - "SafeTube" real-world video-sharing platform feed.
  - Strict zero-trust publishing filter (`verdict == 'ALLOW'`).
  - Streaming endpoint blocks quarantined video streaming with HTTP 403 Forbidden.
- **Speaker Notes:** "To demonstrate real-world impact, we built SafeTube, a video-sharing platform clone. Quarantined videos are strictly prevented from loading or streaming on the public feed."

---

### Slide 10: Interactive Frame Inspection Gallery
- **Header Category:** INVESTIGATIVE TOOLING
- **Title:** Interactive Frame Inspection Gallery
- **Subtitle:** Deep Forensic Inspection with Side-by-Side Comparison
- **Content:**
  - Grid view of all decoded frames with colored borders.
  - Filter chips for All, Legitimate, Suspicious, Uncertain.
  - Lightbox modal displaying full resolution and side-by-side adjacent frame comparison (Previous vs Current vs Next).
  - Jump-to-next-suspicious scrubber.
- **Speaker Notes:** "Administrators can inspect every single extracted frame in the gallery, compare neighboring frames side-by-side, and verify why the AI flagged the frame."

---

### Slide 11: Interactive Timeline & Segment Clustering
- **Header Category:** TEMPORAL ANALYSIS
- **Title:** Interactive Timeline & Segment Clustering
- **Subtitle:** Temporal Mapping of Discontinuities Across the Stream
- **Content:**
  - Colored timeline marker ticks across the full video duration.
  - Automated clustering of consecutive suspicious frames into named Suspicious Segments.
  - Accurate millisecond boundaries (e.g. `Frames 25–25, 00:00:01.042 - 00:00:01.042`).
- **Speaker Notes:** "The video timeline maps out every frame across time and automatically clusters consecutive flagged frames into suspicious segments."

---

### Slide 12: Security Operations Center (SOC) Console
- **Header Category:** OPERATIONAL SECURITY
- **Title:** Security Operations Center (SOC) Console
- **Subtitle:** Active Quarantine Management & Cryptographic Audit Trail
- **Content:**
  - Real-time Chart.js decisions & frame distribution graphs.
  - Active Quarantine Queue with human-in-the-loop Approve/Reject buttons.
  - Tamper-Evident SHA-256 HMAC Audit Ledger: $\text{Row}_i = \text{SHA256}(\text{Row}_{i-1} \parallel \text{Action} \parallel \text{UploadID} \parallel \text{Timestamp})$.
  - "Verify Hash Chain Integrity" button verifies zero ledger tampering.
- **Speaker Notes:** "Our SOC console provides moderation workflows backed by an immutable SHA-256 HMAC audit ledger where past records cannot be altered without breaking the hash chain."

---

### Slide 13: Experimental Validation: 6 Test Scenarios
- **Header Category:** EMPIRICAL RESULTS
- **Title:** Experimental Validation: 6 Test Scenarios
- **Subtitle:** Comprehensive Benchmark Across Realistic Attack Vectors
- **Content:**
  - Scenario 1 (Authentic): 100% RED frames -> ALLOW -> Published.
  - Scenario 2 (Deepfake): 45 GREEN frames -> QUARANTINE -> Blocked.
  - Scenario 3 (Single-Frame): Pinpoints Frame #25 as GREEN -> QUARANTINE.
  - Scenario 4 (Uncertain): Marked YELLOW -> QUARANTINE.
  - Scenario 5 (Corrupted): Malformed bitstream -> BLOCK.
  - Scenario 6 (AI Failure): Simulated model error -> QUARANTINE (Fail-closed).
- **Speaker Notes:** "We implemented a 1-click test launcher for 6 real-world scenarios. Notably in Scenario 3, SafeGate successfully pinpoints a single tampered frame at Frame 25 amid 44 authentic frames."

---

### Slide 14: Automated Testing & Verification
- **Header Category:** VERIFICATION & QUALITY
- **Title:** Automated Testing & Code Quality Suite
- **Subtitle:** 74 Automated Unit, Integration, and Security Tests Passing
- **Content:**
  - 100% pass rate: 74/74 tests passing across 10 test suites in under 15 seconds.
  - Zero regression on all 60 legacy 7-layer OSI tests.
  - 14 comprehensive end-to-end SafeGate 2.0 integration tests (`tests/test_safegate2.py`).
- **Speaker Notes:** "We enforce rigorous software engineering standards: 74 automated tests pass in under 15 seconds, verifying complete backward compatibility and robust security."

---

### Slide 15: Comparative Analysis: SafeGate vs Industry
- **Header Category:** INDUSTRY IMPACT
- **Title:** Comparative Analysis: SafeGate vs Industry
- **Subtitle:** Why In-Line Frame Firewalls Are the Future of Media Security
- **Content:**
  - WAFs: Blind to video payloads.
  - Keyframe Scanners: Vulnerable to single-frame splice attacks.
  - SafeGate 2.0: 100% frame decoding, dual-engine AI, in-line zero-trust gating, and cryptographic auditability.
- **Speaker Notes:** "Compared to commercial alternatives, SafeGate 2.0 provides true in-line protection, full frame decoding, and an immutable cryptographic audit trail."

---

### Slide 16: Conclusion & Future Research Directions
- **Header Category:** CONCLUSION
- **Title:** Conclusion & Future Research Directions
- **Subtitle:** Summary of Deliverables & Project Contributions
- **Content:**
  - Complete deliverables: Working repository, responsive web platform, A1 poster, video demo, and capstone documentation.
  - Future work: Audio-visual multimodal sync, TensorRT acceleration for 4K streaming, and decentralized blockchain anchoring.
- **Speaker Notes:** "In conclusion, SafeGate 2.0 demonstrates that frame-level deepfake firewalling is technically feasible and essential. Thank you, and I look forward to your questions."
