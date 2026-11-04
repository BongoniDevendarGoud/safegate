# SafeGate 2.0 — Capstone Demonstration Video Script & Storyboard

**Project Title:** SafeGate 2.0: AI-Powered Website Video Upload Firewall & Frame-Level Deepfake Detection System  
**Candidate Name:** Bongoni Devendar Goud (Roll No: 2103A52001)  
**Program:** B.Tech in School of Computer Science & Artificial Intelligence, SR University  
**Target Video Duration:** 8 Minutes 15 Seconds (Complies with 5–12 minute guideline)  
**Student On-Camera Presence:** 2 Minutes 15 Seconds (27.3% of total duration, exceeding 20% minimum)  

---

## Technical & Audio-Visual Setup Checklist
- **Video Resolution:** 1080p Full HD (1920 × 1080) @ 30 FPS.
- **Audio:** External USB Condenser Microphone with noise suppression filter.
- **Recording Software:** OBS Studio with split-screen webcam overlay and display capture.
- **On-Screen Captions:** Auto-generated English subtitles enabled throughout.

---

## Detailed Storyboard & Narration Timeline

### Segment 1: Opening Title Card (00:00 – 00:15) [15 Seconds]
- **Visual:** Full-screen high-resolution title slide with SR University logo, Department badge, and project metadata.
- **On-Screen Text:**
  ```text
  SR UNIVERSITY — SCHOOL OF COMPUTER SCIENCE & ARTIFICIAL INTELLIGENCE
  CAPSTONE PROJECT FINAL DEMONSTRATION (2026-2027)
  PROJECT: SafeGate 2.0: AI-Powered Website Video Upload Firewall
  STUDENT: Bongoni Devendar Goud (Roll No: 2103A52001)
  INTERNAL GUIDE: Dr. CH. Sandeep, Associate Professor & Head, School of CS&AI
  DEAN: Dr. M. Sheshikala | COORDINATOR: Mr. Sallauddin Md
  ```
- **Spoken Audio (Voiceover):** "Welcome to the Capstone Project demonstration of SafeGate 2.0: An AI-Powered Website Video Upload Firewall and Frame-Level Deepfake Detection System, presented by Bongoni Devendar Goud, SR University School of Computer Science and Artificial Intelligence."

---

### Segment 2: Student Camera Introduction & Problem Definition (00:15 – 01:15) [60 Seconds] — **STUDENT ON CAMERA**
- **Visual:** Full-screen webcam video of Bongoni Devendar Goud in formal attire, clear lighting, looking directly into the camera.
- **Spoken Narration:**
  "Respected panel members and viewers, modern social media and video platforms face an unprecedented cybersecurity challenge: weaponized deepfakes and generative AI video tampering.
  Traditional Web Application Firewalls, such as Cloudflare or AWS WAF, are blind to multimedia payloads. They inspect HTTP headers and SQL injection signatures, allowing uploaded video files to pass straight into publishing datastores unexamined. Once a deepfake is published to a content delivery network, the reputational and social harm is irreversible.
  Furthermore, existing commercial scanners only sample one or two frames per second, which completely misses temporal splice attacks where an attacker alters just a fraction of a second.
  To solve this, I designed and implemented SafeGate 2.0: an in-line upload firewall that sits between uploaders and the website backend, decoding every single frame, running dual-engine AI classification, and strictly gating publication with zero-trust policies."

---

### Segment 3: System Architecture & OSI Stack Walkthrough (01:15 – 02:30) [75 Seconds]
- **Visual:** Screen recording showing architecture diagram, transitioning to the 7-Layer OSI stack. Webcam in lower-right corner.
- **Spoken Narration:**
  "Let us examine the architecture of SafeGate 2.0. The system operates as an active proxy firewall. When a user uploads a video to our demo video platform, SafeGate immediately intercepts the file and buffers it into a non-executable quarantine sandbox.
  The pipeline executes across eight specialized stages:
  First, file validation and magic byte inspection.
  Second, metadata extraction for duration, resolution, and container integrity.
  Third, our 100% Complete Decoded Frame Extraction Engine. Using OpenCV and FFmpeg, every single frame is extracted—a 60-second video at 30 FPS yields exactly 1,800 decoded frames, with zero downsampling and individual SHA-256 fingerprinting.
  Fourth, our Dual-Engine AI Detection combines a PyTorch frequency-domain convolutional network with physical forensic indicators: JPEG recompression residual MSE, Laplacian edge variance, and inter-frame color histogram correlation.
  Fifth, each frame is stamped with our strict forensic color taxonomy: RED for Legitimate, GREEN for Suspicious/AI, and YELLOW for Uncertain.
  Finally, our Risk Assessment engine computes a composite 0-to-100 risk score and enforces a policy: ALLOW, QUARANTINE, or BLOCK."

---

### Segment 4: Live Website Demonstration & The 6 Scenarios (02:30 – 06:00) [210 Seconds]
- **Visual:** Full-screen browser capture navigating the live SafeGate 2.0 web platform at `http://localhost:8000`.

#### Step 4A: The Demo Video-Sharing Platform (02:30 – 03:15)
- **Visual:** Navigating to `tab-website` ("SafeTube").
- **Spoken Narration:**
  "Here is our demo video-sharing website, simulating a real-world platform like YouTube. Under our zero-trust publishing firewall, only videos that have received an ALLOW decision are published on this feed. Notice that unverified or quarantined media is strictly inaccessible."

#### Step 4B: Live Upload & Scenario 1 (Authentic Video) (03:15 – 04:00)
- **Visual:** Clicking Scenario 1 (`Authentic Video`). Real-time scanner advances across all 8 stages to 100%.
- **Spoken Narration:**
  "Let us test Scenario 1: an authentic video recorded by an optical CMOS camera. As we trigger the scan, SafeGate decodes all 45 frames. The PyTorch frequency model and optical heuristics confirm natural noise and focus consistency. All 45 frames are marked RED. The risk score is 0 out of 100, yielding an ALLOW verdict. Returning to the public feed, we see the video has been automatically approved and is instantly playable."

#### Step 4C: Scenario 2 & 3 (Deepfake & Single-Frame Tamper) (04:00 – 05:15)
- **Visual:** Clicking Scenario 3 (`Single-Frame Tamper`). Scanner completes with QUARANTINE verdict. Navigating to the Frame Gallery and Timeline.
- **Spoken Narration:**
  "Now, let us examine our most demanding test: Scenario 3, a single-frame temporal splice attack. Here, 44 frames are authentic, but exactly one frame—Frame #25—has injected synthetic noise.
  Notice the precision of SafeGate 2.0: in the Video Timeline, the entire scrubber is RED, with exactly one prominent GREEN marker at timestamp 00:00:01.042.
  Switching to the Frame Gallery, we can filter for Suspicious frames. Opening Frame #25 in our deep comparison modal, we see the adjacent frames side-by-side: Frame 24 is clean RED, Frame 25 is flagged GREEN with high JPEG residual MSE, and Frame 26 is clean RED.
  Because even a single frame was tampered, SafeGate's policy engine immediately routed the video to QUARANTINE, completely blocking it from reaching the public video feed."

#### Step 4D: SOC Moderation & Audit Ledger (05:15 – 06:00)
- **Visual:** Navigating to `tab-admin` (SOC Moderation Dashboard). Showing Chart.js graphs, clicking "Approve", then clicking "Verify Hash Chain Integrity".
- **Spoken Narration:**
  "Here in the SOC Moderation Dashboard, security analysts have full visibility into decisions and frame distributions via Chart.js telemetry.
  In the Quarantine Queue, administrators can review held videos and perform human-in-the-loop overrides.
  Below, our tamper-evident SHA-256 HMAC audit ledger cryptographically chains every single event. Clicking 'Verify Hash Chain Integrity' dynamically recalculates every block's SHA-256 hash pointer to guarantee zero retroactive tampering."

---

### Segment 5: Automated Test Suite & Code Verification (06:00 – 06:45) [45 Seconds]
- **Visual:** Terminal window running `pytest tests/`. All 74 tests pass in green.
- **Spoken Narration:**
  "To ensure mission-critical stability, SafeGate 2.0 is backed by a comprehensive automated test suite. Running pytest executes 74 automated unit, integration, and security tests in under 15 seconds with a 100% pass rate. This verifies all 60 legacy 7-layer OSI tests alongside our 14 new SafeGate 2.0 end-to-end integration tests."

---

### Segment 6: Student Camera Conclusion & Acknowledgements (06:45 – 08:00) [75 Seconds] — **STUDENT ON CAMERA**
- **Visual:** Full-screen webcam of Bongoni Devendar Goud speaking with conviction and summary slides.
- **Spoken Narration:**
  "In conclusion, SafeGate 2.0 demonstrates that frame-level deepfake firewalling is not only theoretically viable but practically deployable in modern web platforms.
  By eliminating keyframe subsampling, pairing neural frequency classifiers with physical optical heuristics, enforcing an inverted forensic color taxonomy, and placing an impenetrable zero-trust gate before publication, SafeGate 2.0 prevents synthetic media from polluting our digital information ecosystem.
  I extend my heartfelt gratitude to my project guide and Head of the School of CS&AI, Dr. CH. Sandeep, our Dean, Dr. M. Sheshikala, and our coordinator, Mr. Sallauddin Md, for their invaluable guidance throughout this Capstone project.
  The entire platform is fully open-source and documented on GitHub. Thank you for your time, and I am now ready for the panel's questions."

---

### Segment 7: Closing Title Card (08:00 – 08:15) [15 Seconds]
- **Visual:** Full-screen closing card with SR University logo, contact info, and repository link.
- **On-Screen Text:**
  ```text
  THANK YOU!
  PROJECT: SafeGate 2.0: AI-Powered Website Video Upload Firewall
  CANDIDATE: Bongoni Devendar Goud (Roll No: 2103A52001)
  INSTITUTION: SR University, Warangal, Telangana - 506371
  DEPARTMENT: School of Computer Science & Artificial Intelligence
  GITHUB: https://github.com/BongoniDevendarGoud/safegate
  ```
- **Spoken Audio:** Soft closing theme music fadeout.
