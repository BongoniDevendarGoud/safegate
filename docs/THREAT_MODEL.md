# SafeGate — Threat Model (STRIDE Methodology)

> **Design Philosophy:** SafeGate is engineered to be **fail-closed and tamper-resistant**. 
> No automated content moderation architecture is 100% bypass-proof. This document provides an honest, 
> rigorous engineering analysis of potential attack vectors, architectural mitigations, and known limitations.

---

## 1. STRIDE Threat Analysis Matrix

| Threat Category | Specific Threat Description | Technical Mitigation in SafeGate | Residual Risk & Known Limitations |
| :--- | :--- | :--- | :--- |
| **Spoofing** | **Replay of Blocked Uploads:** An attacker repeatedly re-uploads the exact prohibited video file. | **Stage 2 Exact SHA-256 Blocklist:** Instant $O(1)$ database lookup blocks identical payloads before running ML stages. | Trivial byte-level perturbations (e.g. changing 1 byte) alter the SHA-256 completely. Addressed by Stage 4 pHash. |
| **Spoofing** | **Client / Identity Spoofing:** An unauthorized entity tries to access moderator review queues or purge blocklists. | **API Key Header Authentication:** Strict separation between `CLIENT_API_KEY` and `ADMIN_API_KEY` using constant-time `hmac.compare_digest`. | API keys stored in client applications could be extracted via reverse engineering if distributed publicly. |
| **Tampering** | **Re-encoding Evasion:** Attacker re-encodes prohibited video at different bitrates, framerates, or codecs to evade hash matches. | **Stage 4 Perceptual Hashing (pHash):** 64-bit DCT perceptual hashes survive recompression and rescaling within Hamming distance $\le 10$. | Extreme temporal reordering, frame interpolation, or severe spatial warping can exceed the Hamming threshold. |
| **Tampering** | **Cropping & Aspect Ratio Modification:** Attacker crops video margins or places content in picture-in-picture window. | **Stage 5 Vision Transformer (ViT):** Local model analyzes semantic features across frames regardless of borders. | Sub-region explicit content occupying $<5\%$ of total frame area may score below `BLOCK_THRESHOLD`. |
| **Tampering** | **Adversarial Perturbation / Noise:** Attacker adds imperceptible high-frequency adversarial noise designed to fool neural networks. | **Fail-Closed Multi-Stage Ensemble:** Borderline scores $[0.45, 0.85)$ trigger Gemini second opinion; noise often causes deepfake residual spikes. | Targeted universal adversarial perturbations against specific ViT architectures remain an open research challenge. |
| **Repudiation** | **Audit Log Tampering:** An attacker or compromised moderator attempts to delete or alter historical upload records in SQLite. | **Cryptographic Hash Chain:** Each audit record chains `row_hash = SHA256(previous_hash + payload)`. `/api/audit/verify` detects breaks. | An attacker with raw SQLite root file write access could theoretically rewrite the entire table from the break forward. |
| **Information Disclosure** | **Stack Trace / Schema Leakage:** Attacker sends malformed payloads to trigger unhandled exceptions revealing paths or versions. | **Global Exception Handler & Pydantic:** Suppresses stack traces; returns generic HTTP 500/422 responses with sanitized schemas. | Timing side-channels on model inference duration can reveal whether a video has complex visual features. |
| **Information Disclosure** | **Prohibited Imagery Storage:** Gateway disk could be inspected to access explicit material. | **Zero-Image Retention Policy:** Prohibited videos are unlinked (`unlink()`) immediately on `BLOCK`. Only hashes and timestamps are kept. | Residual blocks in unallocated disk space could theoretically be recovered before OS block overwrite (mitigated by full disk encryption). |
| **Denial of Service** | **Storage & Memory Exhaustion:** Attacker uploads multi-gigabyte files to exhaust gateway RAM and disk storage. | **Stage 1 Size Bounds:** Strict `MAX_UPLOAD_SIZE_MB` (default 200MB) checked via atomic temp writes before pipeline admission. | Distributed botnet attacks can saturate upstream gateway network bandwidth prior to application inspection. |
| **Denial of Service** | **Processing Exhaustion (Zip/Video Bombs):** High-framerate or malformed container designed to cause infinite loops in OpenCV. | **Frame Extraction Cap (`MAX_FRAMES`):** Hard cap (default 60 frames) sampled at fixed temporal intervals; fail-closed timeout routing. | Highly malformed codecs could exploit underlying native C/C++ memory vulnerabilities in FFmpeg/libav. |
| **Denial of Service** | **API Flooding:** Rapid upload requests from a single source attempting to starve processing threads. | **IP Rate Limiting:** `slowapi` enforces configurable limits (default 10 requests/minute per IP) with HTTP 429 Retry-After headers. | IP rotation via residential proxies can partially circumvent per-IP rate limits. |
| **Elevation of Privilege** | **Path Traversal via Malicious Filenames:** Filenames like `../../../../etc/shadow` attempting to overwrite system binaries. | **UUID Normalization & `is_relative_to`:** All user filenames are discarded; random UUID4 names are enforced within verified folders. | Misconfiguration of parent folder permissions could expose quarantine directories if run as OS root user. |

---

## 2. Security Boundaries & Fail-Closed Assertions

1. **Untrusted Inputs:** All incoming video payloads, filenames, and headers are treated as hostile.
2. **Boundary Checks:** Type verification is performed via binary magic bytes (`filetype`), never file extensions.
3. **Fail-Closed State Machine:** If any detector, library, or API returns an error or times out:
   $$\text{Verdict} \leftarrow \text{REVIEW}$$
   $$\text{Prohibited content is NEVER mistakenly allowed.}$$
