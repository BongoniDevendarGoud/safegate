# SafeGate — 7-Layer OSI Security Architecture & CLI Appliance Guide

## 1. Why an OSI Model Architecture?

In traditional software design, web applications often conflate transport parsing, image decoding, security checks, and machine learning into monolithic controllers.

**SafeGate re-engineers video content moderation as a 7-Layer OSI Protocol Stack**:
1. **Defense-in-Depth**: Malicious or malformed payloads are filtered at lower layers (e.g. Layer 1 bitstream bounds, Layer 3 rate limiting, Layer 4 exact hashes, Layer 6 syntax) **before** consuming expensive deep learning and cloud GPU compute at Layer 7.
2. **Fail-Closed Encapsulation**: Each layer operates as an independent security boundary. An anomaly at *any* layer immediately aborts transit and drops the payload into quarantine (`REVIEW`) or destruction (`BLOCK`).
3. **Headless Security Appliance**: Removes all website/HTML overhead. Operates as a pure **terminal CLI tool** and **headless protocol server** returning strict protocol headers (`X-SafeGate-Verdict: ALLOW | BLOCK | REVIEW`, `X-SafeGate-OSI-Layers: L1-L7`).

---

## 2. Complete OSI Layer Mapping

| Layer | Standard OSI Definition | SafeGate Subsystem | Module | Operational Function |
|---|---|---|---|---|
| **Layer 7** | **Application** | AI Policy & Governance | `app/osi/layer7_application.py` | Local Vision Transformer (`Falconsai/nsfw`), Gemini cloud second opinion, synthetic manipulation / deepfake forensics, and fail-closed policy decision gate. |
| **Layer 6** | **Presentation** | Syntax & Perceptual Encoding | `app/osi/layer6_presentation.py` | Magic-byte container syntax validation (rejecting disguised binaries), RGB transcoding, and 64-bit DCT perceptual hashing (`pHash`) for fuzzy deduplication. |
| **Layer 5** | **Session** | Auth & State Audit Chaining | `app/osi/layer5_session.py` | Constant-time credential authentication (`hmac.compare_digest`), role separation, and cryptographic SHA-256 hash chaining for tamper-evident audit logging. |
| **Layer 4** | **Transport** | End-to-End Checksums & Deduplication | `app/osi/layer4_transport.py` | Exact cryptographic SHA-256 transport checksum calculation and $O(1)$ indexed lookup in `blocklist_hashes`. |
| **Layer 3** | **Network** | Origin IP Traffic Policing | `app/osi/layer3_network.py` | Client IP address tracking, CIDR validation, and sliding-window rate limiting to defend against volumetric flood attacks. |
| **Layer 2** | **Data Link** | Video Framing & Temporal Sync | `app/osi/layer2_datalink.py` | Delineates the continuous bitstream into discrete video frames using temporal sampling (first frame, 1 frame/2s, last frame) with a bounded frame cap. |
| **Layer 1** | **Physical** | Bitstream Ingestion & Buffer Quotas | `app/osi/layer1_physical.py` | Chunked raw byte streaming (64 KB chunks), zero-trust byte size enforcement (`MAX_UPLOAD_SIZE_MB`), and memory-safe spooling. |

---

## 3. The 7-Layer Packet Journey

```text
Incoming Video Packet / Stream
   │
   ▼
[Layer 5: Session Layer] ─────────> Authenticate Session Token (Constant-time comparison)
   │
   ▼
[Layer 3: Network Layer] ─────────> Police IP Rate Limits (10 req/min sliding window)
   │
   ▼
[Layer 1: Physical Layer] ────────> Buffer Raw Bitstream (Enforce 200 MB hard cap)
   │
   ▼
[Layer 6: Presentation Syntax] ───> Inspect Binary Magic Bytes (Verify genuine MP4/WebM)
   │
   ▼
[Layer 4: Transport Layer] ───────> Compute SHA-256 Checksum (Instant BLOCK if in blocklist)
   │
   ▼ (Quarantine Spooling)
   │
   ▼
[Layer 2: Data Link Layer] ───────> Sample Discrete Frames & Synchronize Timestamps
   │
   ▼
[Layer 6: Presentation Encoding] ─> Compute 64-bit DCT pHashes (BLOCK if Hamming dist <= 10)
   │
   ▼
[Layer 7: Application Layer] ─────> Classify ViT NSFW scores, consult Gemini, analyze deepfake heuristics
   │
   ▼
[Layer 5: Session Checkpoint] ────> Commit to SHA-256 Tamper-Evident Hash Chain
   │
   ▼
Enforce Storage Action:
   - ALLOW  -> Move to published/
   - REVIEW -> Move to review/
   - BLOCK  -> Unlink file & index fingerprints
```

---

## 4. Standalone CLI Tool (`cli.py`)

SafeGate includes a terminal command-line tool with color-coded layer diagnostics:

### 4.1 Screen a Video File
```bash
python cli.py scan sample_clean.mp4
```

**Terminal Output:**
```text
======================================================================
  SafeGate -- 7-Layer OSI Video Screening Gateway & CLI Appliance
======================================================================
Architecture: OSI Model Layers 1-7 | Mode: Fail-Closed & Tamper-Resistant

Initiating OSI Protocol Stack Analysis on: sample_clean.mp4
Size: 53,855 bytes | Client IP: 127.0.0.1

LAYER        SUBSYSTEM                        STATUS     LATENCY    DETAILS
-------------------------------------------------------------------------------------
Layer 5      Session (Authentication)         PASS          0.0ms  Session authenticated successfully for role 'client'.
Layer 3      Network (Traffic Policing)       PASS          0.0ms  IP 127.0.0.1 network traffic conforms to policy (1/10).
Layer 1      Physical (Bitstream Ingestion)   PASS          0.2ms  Stream buffered safely (53855 bytes).
Layer 6      Presentation (Syntax Validation) PASS          4.0ms  MIME format confirmed: video/mp4 (.mp4)
Layer 4      Transport (Integrity & Exact Match) PASS          6.3ms  SHA-256 clean: d0be492050488172...
Layer 2      Data Link (Temporal Framing)     PASS         51.8ms  Extracted 3 synchronized frames.
Layer 6      Presentation (pHash Deduplication) PASS        576.7ms  Computed 3 frame pHashes. Blocklist clean.
Layer 7      Application (Cognitive Policy Gate) ALLOW        78.2ms  NSFW: 0.02, Deepfake: 10/100 -> ALLOW
-------------------------------------------------------------------------------------

>>> FINAL VERDICT: ALLOW (Published) <<<
Upload ID:       8ffd4852aa5a4e7790a85ba90bb5c6df
SHA-256:         d0be4920504881722653251bb916fd116bdcb7244f67a1db22c112feef2a11b9
NSFW Peak:       2.0%
Deepfake Risk:   10/100
Pipeline Time:   0.719 seconds
Explanation:     Clean: Media cleared all screening stages without triggering security thresholds.
```

### 4.2 Verify Cryptographic Audit Chain
```bash
python cli.py audit
```
**Output:**
```text
Verifying Cryptographic SHA-256 Audit Hash Chain...
-----------------------------------------------------------------
[+] AUDIT INTEGRITY: VALID (Cryptographic Chain Intact)
Total Sequential Records: 1
Broken at Row ID:         None
Verification Summary:     Audit chain verified: all 1 entries are cryptographically intact.
-----------------------------------------------------------------
```

### 4.3 Inspect Telemetry & Blocklists
```bash
python cli.py stats
python cli.py blocklist
```

---

## 5. Headless Network Server Daemon (`app/server.py`)

To run SafeGate purely as a protocol daemon (no HTML or browser frontend):

```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

### Protocol Interaction with `curl`:
```bash
curl -X POST http://127.0.0.1:8000/osi/scan \
     -H "X-API-Key: dev-client-key-change-in-production-98765" \
     -F "file=@sample_clean.mp4" \
     -i
```

**HTTP Protocol Headers Emitted:**
```http
HTTP/1.1 200 OK
X-SafeGate-Verdict: ALLOW
X-SafeGate-Upload-Id: 8ffd4852aa5a4e7790a85ba90bb5c6df
X-SafeGate-Latency: 0.719
X-SafeGate-OSI-Layers: L1-L7
Content-Type: application/json
```

**JSON Body with Layer-by-Layer Trace:**
```json
{
  "upload_id": "8ffd4852aa5a4e7790a85ba90bb5c6df",
  "verdict": "ALLOW",
  "explanation": "Clean: Media cleared all screening stages.",
  "scan_duration_sec": 0.719,
  "sha256": "d0be4920504881722653251bb916fd116bdcb7244f67a1db22c112feef2a11b9",
  "nsfw_worst_score": 0.02,
  "deepfake_risk_score": 10,
  "osi_layer_trace": [
    {"layer": 5, "name": "Session (Authentication)", "status": "PASS", "latency_ms": 0.01},
    {"layer": 3, "name": "Network (Traffic Policing)", "status": "PASS", "latency_ms": 0.02},
    {"layer": 1, "name": "Physical (Bitstream Ingestion)", "status": "PASS", "latency_ms": 0.21},
    {"layer": 6, "name": "Presentation (Syntax Validation)", "status": "PASS", "latency_ms": 4.02},
    {"layer": 4, "name": "Transport (Integrity & Exact Match)", "status": "PASS", "latency_ms": 6.31},
    {"layer": 2, "name": "Data Link (Temporal Framing)", "status": "PASS", "latency_ms": 51.84},
    {"layer": 6, "name": "Presentation (pHash Deduplication)", "status": "PASS", "latency_ms": 576.71},
    {"layer": 7, "name": "Application (Cognitive Policy Gate)", "status": "ALLOW", "latency_ms": 78.22}
  ]
}
```

---

## 6. Viva Defense: Questions an Examiner Will Ask

### Q: Why map video screening to the OSI model instead of building a normal application?
**A:** In computer systems security, layered architectures (like the OSI model and DoD TCP/IP stack) enforce **strict abstraction boundaries**. By handling raw bytes at Layer 1, framing at Layer 2, rate limiting at Layer 3, checksum integrity at Layer 4, session tokens and audit chains at Layer 5, syntax and perceptual encoding at Layer 6, and cognitive AI policies at Layer 7, SafeGate achieves:
- **Performance Optimization**: Malformed or blocklisted uploads are terminated at lower layers (L1-L4) in milliseconds before expensive deep neural networks (L7) are invoked.
- **Fail-Closed Security**: Every layer can independently abort transit.
- **Academic Rigor**: It demonstrates mastery of both networking fundamentals (OSI Layers 1-7) and modern machine learning defenses.
