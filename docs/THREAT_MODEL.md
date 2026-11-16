# SafeGate — Threat Model & Security Architecture

## 1. Overview & Scope
This document specifies the threat model for the SafeGate Media-Integrity Firewall. SafeGate operates as an untrusted-input processing perimeter, ingesting binary media payloads (video/image files) from potentially adversarial clients and issuing cryptographically verified publication clearances.

---

## 2. Threat Actor Taxonomy
1. **Adversarial Media Creators:** Disinformation actors, fraudulent impersonators, or extortionists attempting to publish deepfakes or non-consensual imagery.
2. **Malicious File Authors:** Attackers crafting weaponized media containers (e.g., FFmpeg exploit payloads, zip bombs, OOM triggers, buffer overflows).
3. **Malicious / Compromised Host Apps:** Clients trying to bypass quarantine, replay stale clearance tokens, or spoof webhook confirmations.
4. **Malicious Insiders / Rogue Reviewers:** Operators attempting to illicitly approve blocked content or tamper with moderation audit logs.

---

## 3. STRIDE Analysis & Attack Surface Matrix

| Threat Category | Attack Vector / Scenario | Architectural Mitigation |
| :--- | :--- | :--- |
| **Spoofing** | Forging webhook callbacks or spoofing publish clearance tokens. | All outgoing webhooks are signed using HMAC-SHA256 (`X-SafeGate-Signature`) with per-tenant rotating keys. Clearance tokens are short-lived, encrypted JWTs tied to content SHA-256. |
| **Tampering** | Modifying historical audit records or mutating quarantined files before review. | Tamper-evident HMAC-SHA256 hash-chained ledger. Quarantined objects stored in append-only / WORM S3 buckets with strict cryptographic checksum matching (`X-Content-SHA256`). |
| **Repudiation** | Reviewer approves illicit content and denies responsibility. | All moderation console interactions require authenticated reviewer identity, tied to session keys and recorded in the hash-chained audit ledger. |
| **Information Disclosure** | Leakage of sensitive/CSAM content via worker logs, caching proxies, or reviewer monitors. | Strict PII and token redaction filter in structured logger. Restricted CSAM escalation pipeline completely bypasses general worker queues and databases. Reviewer console blurs sensitive imagery by default. |
| **Denial of Service (DoS)** | Decompression bombs, infinite frame streams, out-of-memory decoder exploits. | Strict intake validation: header magic byte check, max file size limits (e.g., 500MB), max duration caps, per-tenant rate limiters, sandboxed streaming frame decoders with timeout budgets. |
| **Elevation of Privilege** | Container breakout via native FFmpeg or PyAV vulnerabilities. | Media decoding and inference workers run in non-root, read-only root filesystem Docker containers with `no-new-privileges: true` and dropped Linux capabilities. |

---

## 4. Adversarial Machine Learning Defenses

### A. Adversarial Perturbations (Evasion Attacks)
- **Threat:** Attackers inject high-frequency noise or imperceptible adversarial gradients to trick deepfake classification models into predicting GREEN.
- **Defenses:**
  - Multi-branch ensemble combining spatial features (CNN/ViT), frequency domain analysis (FFT/DCT power spectrums), and temporal trajectory metrics (head pose/blink/jitter).
  - Spatial pre-filtering (adaptive Gaussian blurring, recompression normalization) during ingestion.
  - Multi-frame temporal confirmation requirements (individual adversarial frames cannot force an ALLOW if neighbors or aggregate uncertainty elevate).

### B. Concept Drift and Zero-Day Generators
- **Threat:** Emergence of novel diffusion architectures (e.g., Sora, Flux, Wan, Kling) whose synthetic signatures evade training distributions.
- **Defenses:**
  - Model uncertainty quantification: when ensemble variance or predictive entropy exceeds $\tau_{\text{uncertainty}}$, frames route to YELLOW (`HUMAN_REVIEW`).
  - Active learning & validation loops (Phase 5) collecting review-escalated samples for continuous offline re-calibration.
