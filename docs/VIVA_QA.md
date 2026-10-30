# SafeGate — Viva Voce Preparation Guide (20 Questions & Answers)

This guide provides technical explanations for the SafeGate architecture, algorithms, and design choices to support project evaluation and viva defense.

---

### Q1: What is the primary problem SafeGate solves, and how does it differ from traditional moderation systems?
**Answer:**  
Most content platforms employ an **asynchronous "post-and-moderate"** model where videos are immediately published to a content delivery network (CDN) and scanned in the background. If a violation is discovered minutes or hours later, the video is retroactively removed. During that window, harmful media can go viral.  
**SafeGate is a synchronous, fail-closed upload gateway**. It places uploads into a quarantine sandbox and subjects them to an 8-stage verification pipeline *before* they are published. A video is only moved to the `published/` folder if all stages pass.

---

### Q2: What does "fail-closed" mean in cybersecurity, and how is it implemented in SafeGate?
**Answer:**  
In defensive security, a system is either **fail-open** (defaults to granting access when an internal failure occurs to maximize availability) or **fail-closed** (defaults to denying access to maximize security and confidentiality).  
In SafeGate, any unexpected condition—such as a corrupted video container, an unhandled codec error, a local model crash, an external Gemini API timeout, or a rate limit—**immediately catches the exception and routes the upload to `REVIEW` (or rejects it outright)**. The system will *never* return an `ALLOW` verdict unless every stage completes with clean signals.

---

### Q3: Why check magic bytes instead of relying on file extensions during intake?
**Answer:**  
File extensions (like `.mp4` or `.avi`) are arbitrary strings supplied by the client and can be trivial to spoof. An attacker can rename an executable (`payload.exe`) or a malicious web script (`shell.php`) to `video.mp4` to bypass naive extension filters.  
SafeGate uses **file signatures (magic bytes)** via the `filetype` library, inspecting the binary header of the payload (e.g., ISO Base Media File Format box headers `ftyp` for MP4, or EBML headers `0x1A45DFA3` for MKV/WebM). If the binary header does not match an allowed video MIME type, the file is rejected at Stage 1 before reaching media decoders.

---

### Q4: How does SafeGate protect against path traversal attacks (e.g., `../../etc/passwd`)?
**Answer:**  
SafeGate implements **Zero-Trust Input Sanitization**:
1. It ignores the user-supplied filename completely for filesystem storage.
2. It generates a cryptographically random 32-character hexadecimal UUID (`uuid.uuid4().hex`) and appends only the validated file extension.
3. The original filename is stored strictly as metadata in the SQLite database for moderator reference and is never concatenated into filesystem paths.

---

### Q5: What is the difference between exact cryptographic hashing (SHA-256) and perceptual hashing (pHash)?
**Answer:**  
- **SHA-256 (Cryptographic Hash)**: Designed with the **Avalanche Effect**—if a single bit changes in the video file, the resulting 256-bit hash changes completely. It is ideal for exact deduplication (Stage 2) in $O(1)$ time, but it cannot detect media that has been re-encoded, slightly compressed, or cropped.
- **pHash (Perceptual Hash)**: Operates in the frequency domain. It converts frames to grayscale, resizes them to $32 \times 32$, and computes a Discrete Cosine Transform (DCT). It retains only low-frequency components where visual features reside. Minor alterations, compression artifacts, and color balance shifts result in almost identical hashes. SafeGate compares pHashes using **Hamming distance** (the number of differing bits). A Hamming distance $\le 10$ indicates matching visual content.

---

### Q6: Why extract frames using temporal sampling rather than analyzing every video frame?
**Answer:**  
A 60-second video at 30 frames per second contains 1,800 frames. Running a deep neural network vision transformer on 1,800 frames would take tens of seconds per video, creating a severe CPU/GPU bottleneck and enabling Denial-of-Service attacks.  
SafeGate uses **temporal sampling**:
- Always extracts the first frame (0.0s) and last frame (to catch tail-end violations).
- Samples 1 frame every 2 seconds (`FRAME_INTERVAL_SEC`).
- Enforces an upper cap (`MAX_FRAMES = 60`).  
This ensures high anomaly detection across the media timeline while keeping scan latency under 3 seconds on standard CPU hardware.

---

### Q7: Why use a hybrid approach (Local Vision Model + Gemini) instead of sending all frames to Gemini?
**Answer:**  
Sending every video frame to a commercial cloud multimodal API introduces significant risks:
1. **Financial Cost**: API pricing per image/token makes full-video screening expensive at scale.
2. **Latency & Bandwidth**: Uploading dozens of high-resolution images over the WAN creates network lag.
3. **Data Privacy**: Routing user media to third-party clouds can violate user expectations or regulations.
4. **Offline Resilience**: If the internet connection drops or API keys expire, a cloud-only system fails.  
**SafeGate's Solution**: The local `Falconsai/nsfw_image_detection` model evaluates all frames offline in milliseconds. **Gemini is invoked strictly as a second opinion for borderline scores $[0.45, 0.85)$**. Clearly safe media ($<0.45$) and clearly explicit media ($\ge 0.85$) never leave the local machine.

---

### Q8: What happens if Gemini triggers a content safety refusal or the request times out?
**Answer:**  
Commercial LLMs often return safety refusals (e.g., `SAFETY` or `HARM_CATEGORY`) when evaluating explicit images. Rather than treating an API refusal as an error or crashing, SafeGate captures the safety refusal, HTTP 429 rate limit, or timeout, marks the result as `uncertain=True`, and **falls closed to `REVIEW`**. A human moderator is prompted to make the determination.

---

### Q9: Why is deepfake detection treated as an advisory score (0-100) rather than auto-blocking media?
**Answer:**  
Automated deepfake detection is inherently **probabilistic** and subject to false positives. Video compression artifacts, low-light camera sensor noise, zoom lens blur, or teleconferencing codecs can mimic manipulation signatures (such as temporal flicker or facial blur).  
Auto-blocking media based on heuristic deepfake scores would censor legitimate user content. Therefore, SafeGate treats deepfake metrics as an **advisory signal**:
- A score $\ge 70$ **never auto-blocks**; it forces the video into the `REVIEW` queue.
- The moderator dashboard displays the specific heuristic flags (e.g., "High temporal flicker", "Lavf synthetic encoder detected") so the moderator can make an informed decision.

---

### Q10: Is SafeGate 100% bypass-proof?
**Answer:**  
**No, and no production security system is 100% bypass-proof.** Describing a system as "unhackable" is a fundamental anti-pattern in security engineering.  
SafeGate is designed to be **fail-closed and tamper-resistant**. As documented in `THREAT_MODEL.md`:
- Highly targeted adversarial noise (gradient-based pixel perturbations) can theoretically cause a vision model to misclassify a frame.
- Novel generative deepfake architectures trained with temporal consistency loss can bypass basic flicker heuristics.  
SafeGate mitigates these limitations through **defense-in-depth**: combining exact hashing, perceptual hashing, local vision models, cloud second opinions, heuristic analysis, and human moderation.

---

### Q11: How does the tamper-evident cryptographic audit log work?
**Answer:**  
SafeGate uses **SHA-256 hash chaining**, identical to the block-linking mechanism in a blockchain or Git commit history:
$$\text{row\_hash}_i = \text{SHA256}(\text{row\_hash}_{i-1} \parallel \text{action} \parallel \text{details} \parallel \text{upload\_id} \parallel \text{created\_at})$$
The very first record (genesis block) uses 64 zeros as its previous hash. Each subsequent row links to the previous row's hash.  
If an attacker accesses the SQLite database and modifies a historical verdict from `BLOCK` to `ALLOW`, or deletes an audit row, the hash chain breaks at that exact row ID. The `/api/audit/verify` endpoint detects the discrepancy and flags the integrity violation.

---

### Q12: Why is the audit log described as "tamper-evident" rather than "tamper-proof"?
**Answer:**  
Because the database is hosted locally on SQLite, an attacker with full root filesystem access could recompute the entire hash chain from the point of modification forward. Therefore, the local log is **tamper-evident**—any casual modification or unauthorized SQL statement is immediately detectable.  
To achieve true **tamper-proofing**, the tip hash of this chain can be anchored to an external append-only transparency log (e.g., Certificate Transparency / Sigstore) or a remote Key Management Service (KMS).

---

### Q13: Why are there two separate API keys (`CLIENT_API_KEY` and `ADMIN_API_KEY`)?
**Answer:**  
This enforces the **Principle of Least Privilege (Separation of Duties)**:
- `CLIENT_API_KEY`: Used by client applications or proxy interceptors that only need permission to submit video files via `POST /api/upload` or submit appeals via `POST /api/appeal`.
- `ADMIN_API_KEY`: Reserved for human moderators. Only this key can view the review queue, access full decision logs, approve/reject quarantined files, and verify audit integrity.  
A compromised client key cannot be used to manipulate the moderation queue or retrieve system logs.

---

### Q14: Why use `hmac.compare_digest` instead of the standard `==` operator for API key verification?
**Answer:**  
The standard string equality operator (`==`) in Python terminates comparison early upon encountering the first non-matching byte. An attacker can measure microscopic network latency differences (a **timing attack**) to determine how many leading characters of a guessed API key were correct.  
`hmac.compare_digest` performs a **constant-time comparison**, taking the same execution time regardless of where a mismatch occurs, which neutralizes timing side-channel attacks.

---

### Q15: How does SafeGate defend against Denial-of-Service (DoS) and volumetric flooding?
**Answer:**  
1. **Rate Limiting**: Integrated `slowapi` limits requests per IP address (default: 10 uploads per minute). Exceeding this returns HTTP 429 Too Many Requests.
2. **File Size Enforcement**: Streaming chunk validation rejects uploads exceeding `MAX_UPLOAD_SIZE` (default: 200 MB) with HTTP 413 Payload Too Large.
3. **Frame Extraction Cap**: Caps extracted frames at `MAX_FRAMES = 60`, preventing attackers from uploading long videos to exhaust CPU and RAM.
4. **Temporary File Isolation**: Failed uploads are unlinked and cleaned up immediately from `quarantine/`.

---

### Q16: How does the network-level interception addon (`mitm/intercept.py`) work?
**Answer:**  
The addon runs inside `mitmproxy`. In a test lab, client devices route their outbound traffic through this proxy, which has trusted root CA certificates installed. When the proxy detects a `POST` request with multipart video data:
1. It pauses the upstream request.
2. It extracts the raw video bytes from the HTTP request body.
3. It forwards the payload to SafeGate's `/api/upload` endpoint.
4. If SafeGate returns `ALLOW`, the proxy resumes forwarding the request upstream.
5. If SafeGate returns `BLOCK` or `REVIEW`, the proxy terminates the request and returns **HTTP 403 Forbidden** with `"Blocked by SafeGate: policy violation"`.
6. If SafeGate is unreachable, the proxy **fails closed** and blocks the upload.

---

### Q17: Why is TLS interception not recommended for production environments?
**Answer:**  
TLS interception decrypts traffic at the network layer, which breaks end-to-end encryption, requires distributing custom Root CAs to client devices, and raises legal, privacy, and compliance concerns.  
In production architectures, media screening is integrated at the **application layer**:
- **API Gateway**: Envoy, Kong, or Cloudflare Workers inspect requests at the edge before passing them to backend microservices.
- **Asynchronous Cloud Storage Triggers**: Users upload directly to an S3/GCS bucket via pre-signed URLs. An S3 Object Lambda or Cloud Function automatically moves the file to a quarantine bucket, triggers SafeGate, and moves it to the public bucket only after verification.

---

### Q18: What are the concurrency implications of using SQLite, and how would this evolve in enterprise production?
**Answer:**  
SQLite uses file-level locking. In high-concurrency environments with hundreds of simultaneous write operations, SQLite can experience `database is locked` contention. SafeGate mitigates this for a mini-project deployment by using WAL (Write-Ahead Logging) mode and short transaction lifecycles.  
For enterprise production, SQLite would be replaced with a distributed relational database like **PostgreSQL** with connection pooling (`pgbouncer`), allowing high concurrent write throughput across multiple container replicas.

---

### Q19: Why does SafeGate delete files on a BLOCK verdict rather than keeping them?
**Answer:**  
**HARD RULE 1: Defensive purpose only; never generate, store, or source explicit content.**  
Retaining prohibited or explicit media introduces severe legal, ethical, and security liabilities (e.g., unauthorized data leakage, operator exposure, or compliance violations under GDPR/local laws). When a file is blocked:
1. SafeGate unlinks the physical file from disk immediately.
2. It retains only the mathematical fingerprints (SHA-256 checksum and frame pHashes).  
Future attempts to upload the exact same file or visually identical frames are blocked at Stages 2 and 4 without re-saving or re-processing the prohibited media.

---

### Q20: How is the Docker deployment hardened for production security?
**Answer:**  
The `Dockerfile` adheres to the **CIS Docker Benchmark**:
1. **Multi-Stage Build**: Separates the build dependencies (compilers, wheel packages) from the lightweight final runtime image, minimizing image size and vulnerabilities.
2. **Non-Root Execution**: Runs under a dedicated service user and group (`safegate:safegate`, UID 10001) rather than `root`.
3. **Dropped Linux Capabilities**: In `docker-compose.yml`, `cap_drop: ALL` and `no-new-privileges:true` prevent privilege escalation attacks.
4. **Volume Isolation**: Quarantined, reviewed, and published directories are mounted as segregated persistent volumes.
