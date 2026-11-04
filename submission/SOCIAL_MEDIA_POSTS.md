# SafeGate 2.0 — Capstone Social Media Dissemination Package

**Author:** Bongoni Devendar Goud (Roll No: 2103A52001)  
**Program:** B.Tech in School of Computer Science & Artificial Intelligence, SR University  
**Project Title:** SafeGate 2.0: AI-Powered Website Video Upload Firewall & Frame-Level Deepfake Detection System  
**Repository:** [https://github.com/BongoniDevendarGoud/safegate](https://github.com/BongoniDevendarGoud/safegate)  

---

## Platform 1: LinkedIn Professional Post

### Audience & Scope
Senior cybersecurity architects, computer vision practitioners, web engineering leaders, AI researchers, and academic mentors.

### Post Text (Copy & Paste)

```markdown
🚨 Beyond Perimeter Firewalls: Protecting Modern Web Platforms Against Weaponized Deepfakes 🛡️

I am thrilled to present our Capstone Project at SR University, School of Computer Science and Artificial Intelligence: SafeGate 2.0 — an AI-Powered Website Video Upload Firewall & Frame-Level Deepfake Detection System!

Every day, millions of multimedia files are published to public video-sharing networks. Yet traditional Web Application Firewalls (WAFs) only examine network-layer packets and text payloads, treating incoming video streams as opaque binary blobs. If an adversary uploads an AI-manipulated or face-swapped video, existing perimeter defenses let it pass directly to the publishing datastore.

SafeGate 2.0 rethinks video security by acting as an in-line, zero-trust gateway:

🔹 Complete Frame Extraction: Unlike superficial scanners that sample 1-2 frames/second, SafeGate 2.0 decodes and extracts 100% of video frames via OpenCV and FFmpeg (1,800 frames for a 60-second video at 30 FPS) with SHA-256 fingerprinting.
🔹 Dual-Engine AI Classification: Combines PyTorch convolutional frequency-domain neural networks with physical forensic heuristics (JPEG compression residual error MSE, Laplacian edge sharpness, and inter-frame color histogram correlation).
🔹 Strict Forensic Color Convention:
   🔴 RED: Legitimate / Authentic Optical Frame
   🟢 GREEN: Suspicious / AI-Manipulated Frame
   🟡 YELLOW: Uncertain / Ambiguous Frame
🔹 Single-Frame Tamper Detection: In our empirical benchmarks, SafeGate successfully pinpointed a single synthetic frame (Frame #25 at 00:00:01.042) hidden among 44 pristine authentic frames.
🔹 Zero-Trust Publishing Firewall: Enforces an automated ALLOW, QUARANTINE, or BLOCK decision. Quarantined media is strictly blocked from the public feed pending SOC moderator determination.
🔹 Tamper-Evident SHA-256 Audit Ledger: Cryptographically chained security events ensure full accountability.

A heartfelt note of gratitude to our Guide and Head of Department, Dr. CH. Sandeep (Associate Professor & Head, School of CS&AI), our Dean, Dr. M. Sheshikala, and our Capstone Project Coordinator, Mr. Sallauddin Md, for their continuous mentorship, encouragement, and technical guidance throughout this journey!

The entire project is open-source with 74 passing automated tests, a full demo video-sharing web application, and Docker support:
🔗 GitHub Repository: https://github.com/BongoniDevendarGoud/safegate

#DeepfakeDetection #Cybersecurity #ArtificialIntelligence #ComputerVision #PyTorch #FastAPI #WebSecurity #ZeroTrust #SRUniversity #SchoolOfCSAI #MachineLearning #DevSecOps #CapstoneProject #OpenSource
```

---

## Platform 2: Twitter / X Thread

### Target Account Tags
- **SR University School of CS&AI:** `@CsaiSru` (https://twitter.com/CsaiSru)
- **Head of School of CS&AI:** `Dr. CH. Sandeep`
- **Institution:** `SR University`

### Tweet Thread (4 Tweets)

#### Tweet 1 / 4 (Hook & Project Introduction)
```text
🚨 Excited to unveil SafeGate 2.0! An AI-powered in-line video upload firewall & frame-level deepfake detection system built for our B.Tech Capstone at @CsaiSru @SRUniversity!

Traditional WAFs treat video uploads as black boxes. SafeGate decodes & screens EVERY single frame before publication. 🛡️🧵👇
```

#### Tweet 2 / 4 (Technical Innovation & Frame Extraction)
```text
2/4 🎞️ 100% Decoded Frame Extraction:
No skipping. No downsampling. A 60s 30FPS video = 1,800 decoded frames with individual SHA-256 hashes.

Powered by a dual-engine architecture:
⚡ PyTorch frequency-domain CNN
⚡ Forensic heuristics (JPEG MSE, Laplacian focus, color correlation)

#DeepfakeAI #CyberSec
```

#### Tweet 3 / 4 (Inverted Forensic Colors & Single-Frame Detection)
```text
3/4 🎨 Strict Forensic Color Marking:
🔴 RED = Legitimate Authentic Frame
🟢 GREEN = AI-Manipulated / Deepfake
🟡 YELLOW = Uncertain / Fail-Closed

In benchmark Scenario 3, SafeGate pinpointed a SINGLE modified frame (Frame #25 at 00:00:01.042) among 44 clean frames! 🎯

#ComputerVision #Python
```

#### Tweet 4 / 4 (Zero-Trust Gating, Mentorship & Open-Source Repo)
```text
4/4 🔒 Zero-Trust: Quarantined videos NEVER reach the public feed!

Special thanks to our mentor Dr. CH. Sandeep (Head, @CsaiSru), Dean Dr. M. Sheshikala & Prof. Sallauddin Md for their leadership!

Code & 74 passing tests on GitHub:
👉 https://github.com/BongoniDevendarGoud/safegate

#SRUniversity #AI
```
