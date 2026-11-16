# SafeGate — Trust & Safety Policy & Operating Guidelines

## 1. Operating Charter
SafeGate empowers online platforms to defend user safety, prevent deceptive synthetic impersonation, and halt the dissemination of illicit media without compromising operational agility or reviewer wellbeing.

---

## 2. Policy Enforcement Matrix

### 🔴 RED Classification (Deepfakes & Manipulated Media)
- **Scope:** 
  - Malicious face replacements (FaceSwap, DeepFaceLab).
  - Synthetic identity cloning / AI puppetry (talking head reenactment).
  - High-confidence diffusion/GAN synthetic fabrications depicting real persons or fraudulent events.
  - Spliced, copy-moved, or forged photographic evidence.
- **Enforcement Action:** Immediate `BLOCK`.
  - The content is strictly prohibited from entering host CDN or streaming endpoints.
  - An immutable audit trail entry is registered.
  - Host apps receive notification with exact timestamps, frame indices, and forensic cues.

### 🟡 YELLOW Classification (Sensitive Content & Uncertainty)
- **Scope:**
  - Non-consensual or graphic violence, bloodshed, or physical trauma.
  - Explicit adult nudity or sexual exploitation.
  - Hate imagery, symbols, or gestures.
  - Low-confidence or uncalibrated model inferences ($\text{Uncertainty} > \tau_{\text{uncertainty}}$).
  - Content with minor temporal anomalies or border manipulation scores ($\tau_{\text{yellow}} \le s < \tau_{\text{red}}$).
- **Enforcement Action:** Immediate `HUMAN_REVIEW`.
  - The upload is held in quarantine.
  - Review queue assignment prioritizes severity and service-level agreements (SLAs).
  - Requires human moderator sign-off before clearance.

### 🟢 GREEN Classification (Authentic Content)
- **Scope:**
  - Content showing consistent natural camera sensor noise, authentic micro-expressions, coherent lighting, and verified absence of sensitive material.
- **Enforcement Action:** Automatic `ALLOW`.
  - Immediate clearance dispatch.

---

## 3. Child Sexual Abuse Material (CSAM) Isolation Protocol

1. **Zero Exposure Mandate:**
   - Any content matching CSAM perceptual hashes (PhotoDNA, PDQ, TMK) or flagged by verified child-safety APIs is **strictly forbidden** from entering regular reviewer queues, worker disk caches, training datasets, or public error logs.
2. **Restricted Legal Escalation Flow:**
   - On hash match confirmation:
     - Worker immediately aborts further feature extraction.
     - Payload is transferred to an isolated, encrypted statutory vault with restricted access control.
     - Automated compliance report is generated for platform Trust & Safety compliance officers to report to the National Center for Missing & Exploited Children (NCMEC) or relevant jurisdictional authorities.
     - All temporary ingestion buffers are cryptographically shredded (`0x00` wipe).

---

## 4. Moderator Wellness & Ergonomic Safeguards

Reviewing flagged media can impose severe cognitive and psychological strain. SafeGate moderation console enforces the following safeguards:
- **Default Visual Obfuscation:** All media in human review is blurred and muted by default. Reviewers must deliberately hover or click to reveal specific frames.
- **Monochrome & Grayscale Mode:** Reviewers can inspect violence or blood in grayscale to reduce visceral impact.
- **Session Limits & Enforced Respite:** Reviewers are automatically prompted for mandatory breaks after 45 minutes of continuous review time.
- **Auditing and Support:** Access to psychological support resources and monitoring of exposure workloads.

---

## 5. Appeals & Dispute Resolution Process

1. **User Notification:** Host applications can provide users with a SafeGate Dispute Reference ID when an upload is blocked.
2. **Re-Review Trigger:** Users or creators may initiate a formal appeal with context or corroborating provenance data (e.g., C2PA Content Credentials, raw camera capture metadata).
3. **Dual-Blind Evaluation:** Appeals are routed to senior Trust & Safety specialists who review the algorithmic evidence package alongside user-provided evidence without exposure to the original automated verdict label.
4. **Correction Feedback Loop:** When an appeal overturns a false positive or negative, the sample is anonymized and routed into the Phase 5 offline calibration benchmark suite.
