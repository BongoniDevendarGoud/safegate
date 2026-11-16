# SafeGate — Product Specification & Requirements

## 1. Executive Summary & Purpose
SafeGate is a production-grade, real-time media-integrity firewall designed as an SDK, middleware, and API that embeds inside host applications (e.g., YouTube/Instagram/TikTok-style platforms, news/streaming services, video-KYC systems). 

SafeGate intercepts and screens every uploaded video or image **before** it is published or made publicly accessible. Content is quarantined upon ingestion and is only released to public storage or CDN when SafeGate returns an explicit `ALLOW` verdict.

SafeGate operates on a **fail-closed** security model: any internal error, timeout, decoding anomaly, or uncalibrated model output routes content to `HUMAN_REVIEW` or `BLOCK`, never to `ALLOW`.

---

## 2. Decision Logic and Frame Color Semantics

SafeGate analyzes media on a per-frame basis (images are treated as single-frame media). Every frame receives exactly one color label:

| Frame Color | Definition | Trigger Conditions |
| :--- | :--- | :--- |
| 🔴 **RED** | **Deepfake / Morphed / Manipulated Content** | Confirmed spatial manipulation (face swaps, facial reenactment, diffusion artifacts, digital splicing), frequency inconsistencies, or temporal jitter/mismatch exceeding calibrated threshold $\tau_{\text{red}}$. |
| 🟡 **YELLOW** | **Sensitive Content / High Model Uncertainty** | Nudity, graphic violence, blood, hate imagery, OR model uncertainty ($\sigma > \tau_{\text{uncertainty}}$), OR borderline manipulation ($\tau_{\text{yellow}} \le s < \tau_{\text{red}}$). |
| 🟢 **GREEN** | **Authentic & Clean Content** | Authenticity verified across all detector branches; manipulation score $< \tau_{\text{yellow}}$, sensitive content score $< \tau_{\text{sensitive}}$, uncertainty low. |

### Content-Level Priority Resolution:
$$\text{RED} \succ \text{YELLOW} \succ \text{GREEN}$$

1. **Any confirmed RED frame $\rightarrow$ `BLOCK`**:
   - The entire upload is immediately blocked from publication.
   - Public CDN / hosting access is withheld.
   - Quarantine artifact is scheduled for deletion per policy, with tamper-evident audit entry and suspicious frame indices/timestamps preserved.
2. **Else, any YELLOW frame $\rightarrow$ `HUMAN_REVIEW`**:
   - The entire upload is quarantined and forwarded to the Trust & Safety Moderation Queue.
   - Reviewer UI displays blurred thumbnails, uncertainty metrics, and timestamp heatmaps.
   - Content is released only upon cryptographically signed human reviewer approval.
3. **Else (Every single frame is GREEN) $\rightarrow$ `ALLOW`**:
   - Upload is cleared for publication.
   - Pre-signed publish tokens or storage transfer webhooks are dispatched to the host application.

---

## 3. Core Invariants & Engineering Principles

1. **Fail-Closed Everywhere**:
   - If media decoding encounters unparseable container headers, audio-video desync, corrupted bitstreams, or decompression bombs, SafeGate immediately issues `BLOCK` or `HUMAN_REVIEW`. It **never** falls back to `ALLOW`.
   - If a model inference worker crashes, runs out of memory, or timeouts, the orchestrator triggers an automated fail-closed review escalation.
2. **Zero Faked Results & Calibrated Operating Points**:
   - No hardcoded accuracy claims (e.g., "100% accurate", "bulletproof").
   - Detection thresholds are calibrated on empirical validation datasets (e.g., FaceForensics++, Celeb-DF v2, DFDC) to achieve pre-defined False Positive Rates (e.g., FPR $\le 0.1\%$ on authentic media).
   - Expected Calibration Error (ECE) and Brier scores are tracked continuously.
3. **Temporal & Ensemble Confirmation**:
   - Single-frame transient false positives are mitigated by temporal smoothing: an isolated spike must be confirmed across temporal neighbors or multi-branch consensus before escalating to `BLOCK`. Borderline cases escalate to `HUMAN_REVIEW` (YELLOW).
4. **Special Child-Safety Escalation Path**:
   - Dedicated pre-inference hash matching against known-CSAM databases (e.g., PhotoDNA / PDQ / TMK hashes via partner APIs).
   - Suspected hits **never** enter general moderation queues or logging sinks; they are immediately isolated into a restricted legal escalation ledger per NCMEC / statutory guidelines.
5. **Tamper-Evident Audit Ledger**:
   - Every file intake, intermediate frame score, aggregate verdict, and human moderation event is recorded in an HMAC-SHA256 hash-chained audit ledger.

---

## 4. Integration Topologies

SafeGate supports three primary integration modalities:
1. **Synchronous Reverse Proxy / Gateway Middleware**:
   - Sits in front of media upload endpoints. Holds HTTP response until initial streaming analysis or synchronous fast-path returns.
2. **Asynchronous Ingestion Worker (Pre-Publish Queue)**:
   - Host app uploads media to a restricted quarantine S3 bucket.
   - SafeGate ingests the object, runs distributed worker pools across frames, emits signed webhooks (`safegate.verdict.ready`), and dispatches SSE updates.
3. **Client-Side SDKs (Python, Node/TypeScript, React)**:
   - Host apps invoke client libraries for pre-flight hash checks, chunked upload signing, and verdict polling.
