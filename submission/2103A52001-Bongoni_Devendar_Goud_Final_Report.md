# SafeGate 2.0: AI-Powered Website Video Upload Firewall & Frame-Level Deepfake Detection System

**A Capstone Project Report Submitted in Partial Fulfillment of Requirement for the Award of the Degree of**  
**BACHELOR OF TECHNOLOGY IN SCHOOL OF COMPUTER SCIENCE AND ARTIFICIAL INTELLIGENCE**  

**Submitted by:**  
**BONGONI DEVENDAR GOUD** (Roll No: 2103A52001)  

**Under the Guidance of:**  
**Dr. CH. SANDEEP**  
Associate Professor & Head, School of Computer Science & Artificial Intelligence  

**Dean of School:** Dr. M. Sheshikala, Professor & Dean  
**Project Coordinator:** Mr. Sallauddin Md, Assistant Professor  

**SR UNIVERSITY**  
Ananthsagar, Hasanparthy, Warangal, Telangana – 506371  
Academic Year: 2026 – 2027  

---

## CERTIFICATE

This is to certify that this project entitled **"SafeGate 2.0: AI-Powered Website Video Upload Firewall & Frame-Level Deepfake Detection System"** is the bonafide work carried out by **BONGONI DEVENDAR GOUD (Roll No: 2103A52001)** as a Capstone Project for the partial fulfillment of the requirements for the award of the degree of **BACHELOR OF TECHNOLOGY in School of Computer Science and Artificial Intelligence, SR University, Ananthsagar, Warangal** during the academic year 2026-2027 under our guidance and supervision.

**Internal Guide:**  
Dr. CH. Sandeep  
Associate Professor & Head, School of CS&AI, SR University  

**Head of School:**  
Dr. CH. Sandeep  
Associate Professor & Head, School of CS&AI, SR University  

**Reviewer-1 (External):** ___________________________  
**Reviewer-2 (Internal):** ___________________________  

---

## ACKNOWLEDGEMENTS

We owe an enormous debt of gratitude to our Capstone Project guide, **Dr. CH. Sandeep**, Associate Professor and Head of the School of Computer Science and Artificial Intelligence, as well as the Dean of the School of CS&AI, **Dr. M. Sheshikala**, Professor, for guiding us from the beginning through the end of the Capstone Project with their intellectual advice, insightful suggestions, and tireless support. We truly value their consistent feedback on our progress, which was always constructive and encouraging, and ultimately drove us in the right direction.

We express our sincere thanks to project coordinator **Mr. Sallauddin Md**, Assistant Professor, School of CS&AI, for his continuous encouragement, organizational coordination, and systematic evaluation milestones throughout this academic semester.

Finally, we express our heartfelt thanks to all the teaching and non-teaching staff of the School of Computer Science and Artificial Intelligence for their suggestions, technical infrastructure access, and timely support throughout the development and testing of SafeGate 2.0.

*Bongoni Devendar Goud (2103A52001)*  

---

## TABLE OF CONTENTS

- **Preliminaries**
  - Title Page
  - Certificate
  - Acknowledgements
  - List of Figures
  - List of Tables
  - List of Acronyms
- **Chapter 1: Abstract & Executive Summary**
- **Chapter 2: About the Organization & Industrial Context**
- **Chapter 3: Introduction to SafeGate 2.0 Project**
- **Chapter 4: Literature Survey & Related Work**
- **Chapter 5: Problem Statement & Security Threat Model**
- **Chapter 6: Requirement Analysis, Feasibility & Risk Assessment**
- **Chapter 7: Proposed Solution & System Architecture**
- **Chapter 8: Detailed Architectural Design, DFDs & State Machines**
- **Chapter 9: Simulation Setup & Implementation Details**
- **Chapter 10: Experimental Results, Scenario Benchmarks & Security Analysis**
- **Chapter 11: Learning Outcomes & Graduate Attributes**
- **Chapter 12: Conclusion, Challenges Faced & Future Directions**
- **References & Technical Citations**
- **Appendix: Project Artefact Links & Source Code**

---

## CHAPTER 1: ABSTRACT & EXECUTIVE SUMMARY

Modern digital society relies extensively on multimedia video-sharing platforms for news dissemination, public education, enterprise communication, and social interaction. However, the rapid democratization and hyper-realistic fidelity of Generative Artificial Intelligence (GenAI)—including Generative Adversarial Networks (GANs), Diffusion models, and face-swapping neural pipelines—have spawned a severe cybersecurity crisis: weaponized multimedia deepfakes. Despite this existential threat, traditional enterprise perimeter defenses such as Web Application Firewalls (WAFs) operate solely at the network, transport, and application text layers, treating uploaded video streams as opaque binary payloads. Consequently, deepfakes slip through standard perimeter filters and infect Content Delivery Networks (CDNs) where the resulting societal, financial, and reputational damage becomes instantaneous and irremediable.

To resolve this fundamental architectural blindspot, this Capstone Project conceives, architects, and implements **SafeGate 2.0**: an enterprise-grade, in-line AI video upload firewall and frame-level deepfake detection system. Designed to sit as an active proxy mediator between public uploaders and website publishing backends (simulating enterprise media platforms such as YouTube or Instagram), SafeGate 2.0 intercepts every incoming video, buffers it into an isolated quarantine sandbox, and subjects it to an exhaustive eight-stage security verification pipeline.

Crucially, SafeGate 2.0 eliminates the fatal vulnerability of keyframe subsampling by implementing a **100% Complete Decoded Frame Extraction Engine**. Powered by OpenCV and FFmpeg stream decoding, the engine guarantees that every single frame (e.g. 1,800 frames for a 60-second video at 30 FPS) is extracted, assigned a millisecond-accurate timestamp, and individually fingerprinted with a cryptographic SHA-256 hash. Extracted frames are evaluated via a **Dual-Engine AI Classifier** combining a PyTorch frequency-domain convolutional neural network with physical forensic optical heuristics (JPEG recompression residual MSE, Laplacian edge focus variance, and inter-frame color histogram correlation).

SafeGate 2.0 enforces a strict, inverted forensic color classification convention: **RED** designates Legitimate/Authentic frames, **GREEN** denotes Suspicious/AI-Manipulated frames, and **YELLOW** indicates Uncertain frames. Videos are scored on a composite 0-to-100 risk scale and gated under a strict zero-trust policy: clean videos receive an `ALLOW` decision and are published to the web feed, whereas videos with even one suspicious or ambiguous frame are locked in `QUARANTINE` with zero public CDN exposure. An immutable, HMAC SHA-256 hash-chained audit ledger cryptographically anchors all decisions. Extensive empirical benchmarking across six realistic scenarios demonstrates 100% detection accuracy on full deepfakes and successfully pinpoints single-frame temporal splice attacks (Frame #25 out of 45 frames). SafeGate 2.0 is validated by 74 automated unit, integration, and security tests passing with zero regressions.

---

## CHAPTER 2: ABOUT THE ORGANIZATION & INDUSTRIAL DOMAIN CONTEXT

### 2.1 Academic Institution: SR University
SR University (SRU), situated in Ananthsagar, Hasanparthy, Warangal, Telangana, is a premier institution renowned for pioneering multidisciplinary innovation, research-led technical education, and societal engineering excellence. The School of Computer Science and Artificial Intelligence (School of CS&AI) at SR University fosters advanced research in cutting-edge computing paradigms, including Artificial Intelligence, Deep Learning, Cybersecurity, Computer Vision, and Distributed Cloud Computing. The Capstone Project curriculum serves as the apex experiential learning milestone, challenging engineering candidates to solve high-impact, real-world industrial and societal problems through rigorous software engineering, empirical verification, and academic discipline.

### 2.2 Industrial Domain Context: The Deepfake Threat
In the contemporary global threat landscape, synthetic media represents one of the most perilous vectors of cyber-warfare, economic destabilization, and personal extortion. Deepfake technology has progressed far beyond academic novelties; automated tools allow non-technical threat actors to generate high-definition impersonations of political leaders, corporate executives, and law enforcement officials within minutes.

Existing commercial countermeasures suffer from two systemic architectural deficiencies:
1. **Post-Publication Blindspot:** Scanners analyze videos only after they have already been ingested into the publishing datastore, leaving a window of vulnerability.
2. **Subsampling Loophole:** Content moderation pipelines inspect only one or two frames per second. Threat actors exploit this by altering as few as 2 to 4 frames (60 to 120 milliseconds). SafeGate 2.0 addresses this industry gap by deploying an in-line, complete-frame upload firewall that neutralizes attacks before publication occurs.

---

## CHAPTER 3: INTRODUCTION TO SAFEGATE 2.0 PROJECT

### 3.1 Project Vision
SafeGate 2.0 operates as an active security firewall between users uploading videos and websites publishing those videos. The system guarantees that no video reaches public availability without passing exhaustive frame-by-frame verification.

```text
USER UPLOAD ➔ SAFEGATE FIREWALL ➔ COMPLETE FRAME EXTRACTION ➔ AI DETECTION ➔ RISK ASSESSMENT ➔ POLICY [ALLOW/QUARANTINE/BLOCK]
```

### 3.2 Seven-Layer OSI Video Security Protocol Model
SafeGate 2.0 maps cybersecurity principles onto an OSI-inspired protocol stack:
- **Layer 1 - Physical Bitstream Ingestion:** Magic byte validation, container verification, non-executable isolation.
- **Layer 2 - Temporal Frame Link:** Complete decoded frame extraction via OpenCV & FFmpeg with zero subsampling.
- **Layer 3 - Transport & Hash Integrity:** Frame-level SHA-256 fingerprinting and blocklist matching.
- **Layer 4 - Perceptual Identity Session:** 64-bit perceptual hashing (pHash) visual blocklisting.
- **Layer 5 - Forensic Presentation:** JPEG compression residual MSE, Laplacian edge focus, and color correlation.
- **Layer 6 - Cognitive AI Application:** PyTorch frequency-domain convolutional neural network.
- **Layer 7 - Firewall Policy Gate:** Composite risk assessment and tri-state decisioning.

---

## CHAPTER 7: PROPOSED SOLUTION & SYSTEM ARCHITECTURE

SafeGate 2.0 introduces three primary technical pillars:

### 1. 100% Decoded Frame Extraction Engine
- Extracts **every single decoded frame** sequentially using `cv2.VideoCapture`.
- Assigns each frame a unique frame ID, millisecond timestamp, and SHA-256 hash.
- Generates stamped visual thumbnails and caches them for fast gallery inspection.
- Enforces strict frame accounting: `extracted_frames == total_decoded_frames`.

### 2. Dual-Engine AI Classification
- **PyTorch Frequency CNN:** Analyzes high-frequency Fourier residuals where neural synthesis leaves spectral artifacts.
- **Optical Forensics:** Evaluates compression error residuals, Laplacian edge focus, and inter-frame color histogram continuity.

### 3. Strict Inverted Forensic Color Taxonomy
- 🔴 **RED:** Legitimate / Authentic Frame (Natural CMOS noise profile).
- 🟢 **GREEN:** Suspicious / AI-Manipulated Frame (Deepfake facial anomalies).
- 🟡 **YELLOW:** Uncertain Frame (Ambiguous / Fail-closed).

---

## CHAPTER 10: EXPERIMENTAL RESULTS & SCENARIO BENCHMARKS

SafeGate 2.0 was evaluated across 6 rigorous benchmark scenarios:

| Scenario | Extracted Frames | Classification Breakdown | Risk Score | Firewall Verdict | Website Feed Response |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **1. Authentic Video** | 45 Decoded | 45 RED (Legitimate) | `0 / 100` | **ALLOW** | Published and playable |
| **2. Deepfake Video** | 45 Decoded | 45 GREEN (Suspicious) | `92 / 100` | **QUARANTINE** | Blocked from public feed |
| **3. Single-Frame Tamper** | 45 Decoded | Frame #25 GREEN, 44 RED | `68 / 100` | **QUARANTINE** | Frame #25 pinpointed at `00:01.042` |
| **4. Uncertain Clarity** | 45 Decoded | 45 YELLOW (Uncertain) | `50 / 100` | **QUARANTINE** | Fail-closed quarantine |
| **5. Corrupted Stream** | 0 Decoded | Header Failure | `100 / 100` | **BLOCK** | File rejected & purged |
| **6. AI Model Failure** | 45 Decoded | Inference Exception | N/A | **QUARANTINE** | Refuses to fail open |

### Automated Testing Suite
- **Total Tests:** 74 passed (0 failed).
- **Execution Time:** 14.65 seconds.
- **Coverage:** Legacy 7-layer stack (60 tests) + SafeGate 2.0 integration (14 tests).

---

## CHAPTER 12: CONCLUSION & FUTURE SCOPE

SafeGate 2.0 demonstrates that frame-level deepfake firewalling is technically viable, robust, and essential for modern multimedia web applications.

### Deliverables Checklist:
1. `submission/BLOG.md` — 685-word technical blog post.
2. `submission/2103A52001-Bongoni_Devendar_Goud_Presentation.pptx` — 16-slide PowerPoint deck.
3. `submission/PRESENTATION_SLIDES.md` — Complete slide-by-slide speaker notes.
4. `submission/poster_a1.html` & `submission/POSTER_A1.md` — Printable A1 project poster.
5. `submission/SOCIAL_MEDIA_POSTS.md` — LinkedIn and Twitter posts tagging `@CsaiSru`.
6. `submission/VIDEO_SCRIPT_AND_STORYBOARD.md` — 8-minute demonstration script with > 25% student on camera.
7. `submission/2103A52001-Bongoni_Devendar_Goud_Links.txt` — Formatted links file.
8. `submission/VIVA_AND_DEMO_GUIDE.md` — Viva defense pitch and panel Q&A bank.
9. `submission/2103A52001-Bongoni_Devendar_Goud_Final_Report.docx` — Complete Capstone Final Report.

---

## REFERENCES
1. A. Rossler et al., "FaceForensics++: Learning to Detect Manipulated Facial Images," in *IEEE ICCV*, 2019.
2. J. Frank et al., "Leveraging Frequency Analysis for Deep Fake Image Recognition," in *ICML*, 2020.
3. Y. Li and S. Lyu, "Exposing DeepFake Videos by Detecting Face Warping Artifacts," in *IEEE CVPRW*, 2019.
4. L. Verdoliva, "Media Forensics and DeepFakes: An Overview," *IEEE JSTSP*, 2020.
5. Open Web Application Security Project (OWASP), "Top 10 Web Application Security Risks," 2021.
