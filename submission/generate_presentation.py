"""
Generate 16-Slide Professional Capstone Presentation for SR University
Project: SafeGate 2.0 - AI-Powered Video Upload Firewall & Frame-Level Deepfake Detection
Candidate: Bongoni Devendar Goud (2103A52001)
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def create_presentation():
    prs = Presentation()
    # 16:9 widescreen
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]

    # Colors
    c_bg = RGBColor(11, 19, 43)        # #0b132b deep navy
    c_card = RGBColor(28, 37, 65)      # #1c2541 card navy
    c_cyan = RGBColor(56, 189, 248)    # #38bdf8 electric cyan
    c_white = RGBColor(248, 250, 252)  # #f8fafc crisp white
    c_muted = RGBColor(148, 163, 184)  # #94a3b8 slate
    c_red = RGBColor(239, 68, 68)      # #ef4444 legitimate red
    c_green = RGBColor(34, 197, 94)    # #22c55e suspicious green
    c_yellow = RGBColor(234, 179, 8)   # #eab308 uncertain yellow

    slides_data = [
        # Slide 1: Title
        {
            "title": "SafeGate 2.0: AI-Powered Website Video Upload Firewall",
            "subtitle": "Frame-Level Deepfake Detection & In-Line Content Verification Gateway",
            "category": "CAPSTONE PROJECT PRESENTATION | ACADEMIC YEAR 2026-2027",
            "bullets": [
                "Candidate Name: Bongoni Devendar Goud (Roll No: 2103A52001)",
                "Program: Bachelor of Technology in School of Computer Science & Artificial Intelligence",
                "Institution: SR University, Ananthsagar, Warangal, Telangana - 506371",
                "Internal Guide: Dr. CH. Sandeep, Associate Professor & Head, School of CS&AI",
                "Dean: Dr. M. Sheshikala, Professor & Dean, School of CS&AI",
                "Project Coordinator: Mr. Sallauddin Md, Assistant Professor, School of CS&AI"
            ],
            "notes": "Good morning respected reviewers and panel members. Today I am presenting my Capstone Project, SafeGate 2.0, an in-line AI video firewall and frame-level deepfake detection system built to protect social media and video-sharing platforms."
        },
        # Slide 2: Problem Statement
        {
            "title": "The Threat Landscape: Deepfakes in Web Applications",
            "subtitle": "Why Traditional Web Application Firewalls (WAFs) Fail",
            "category": "PROBLEM DEFINITION & MOTIVATION",
            "bullets": [
                "Exponential Proliferation of Synthetic Media: Generative AI tools (GANs, Diffusion, Face-Swap) allow instantaneous digital weaponization.",
                "Perimeter Blindspot: Standard WAFs (Cloudflare, AWS WAF) inspect HTTP packets and SQL/XSS signatures, treating video uploads as black-box blobs.",
                "The Damage is Irreversible Post-Publication: Once an unverified video is transcoded and CDN-cached, reputational and financial harm is done within seconds.",
                "Limitations of Existing Tools: Commercial deepfake scanners sample only 1-2 frames/second or inspect static thumbnails, allowing single-frame splice attacks to bypass security.",
                "Core Objective: Create an in-line firewall that intercepts uploads, decodes every frame, and enforces a zero-trust policy before publishing."
            ],
            "notes": "Current web security tools have a fatal blindspot: they treat video files as opaque payloads. If an attacker injects a deepfake face or even a single modified frame, standard firewalls pass it through directly to the publishing datastore."
        },
        # Slide 3: Project Vision & Core Architecture
        {
            "title": "SafeGate 2.0: High-Level Ingestion Firewall Flow",
            "subtitle": "Zero-Trust Mediation Between Uploaders and Publishing Backend",
            "category": "SYSTEM ARCHITECTURE",
            "bullets": [
                "User Uploads Video: Incoming media arrives via multipart/form-data from creator interface.",
                "In-Line Interception: Video is isolated immediately into non-executable Quarantine buffer.",
                "Stage 1: File Validation: Magic bytes verification, MIME checks, and SHA-256 blocklist matching.",
                "Stage 2: Video Metadata Extraction: Container integrity, duration, resolution, and frame rate extraction.",
                "Stage 3: Complete Decoded Frame Extraction: OpenCV/FFmpeg extracts 100% of decoded frames.",
                "Stage 4-5: Dual-Engine AI Detection: PyTorch convolutional classifier and physical forensic heuristics.",
                "Stage 6-8: Risk Assessment & Policy: ALLOW (Publish), QUARANTINE (SOC Review), or BLOCK (Reject)."
            ],
            "notes": "SafeGate 2.0 operates as an active proxy firewall. The demo video-sharing website (SafeTube) cannot publish any video until SafeGate outputs an explicit ALLOW decision."
        },
        # Slide 4: 7-Layer OSI Video Security Protocol
        {
            "title": "Seven-Layer Defense-in-Depth Protocol Stack",
            "subtitle": "Comprehensive Physical to Cognitive Verification Pipeline",
            "category": "THEORETICAL FOUNDATION",
            "bullets": [
                "Layer 1 - Physical Bitstream Ingestion: Magic bytes validation, stream sanitization, non-executable isolation.",
                "Layer 2 - Temporal Frame Link: Complete decoded frame extraction (OpenCV/FFmpeg) with millisecond timestamps.",
                "Layer 3 - Transport & Hash Integrity: SHA-256 frame-level hashing, container metadata validation.",
                "Layer 4 - Perceptual Identity Session: Perceptual hashing (pHash) and visual blocklist matching.",
                "Layer 5 - Forensic Presentation: Compression residuals (MSE), Laplacian sharpness, color histogram continuity.",
                "Layer 6 - Cognitive AI Application: PyTorch frequency-domain deepfake neural classifier & Gemini fallback.",
                "Layer 7 - Firewall Policy Gate: Automated tri-state decisioning (ALLOW, QUARANTINE, BLOCK)."
            ],
            "notes": "Our architecture preserves the 7-layer defense-in-depth model inspired by the OSI stack, extending from raw binary bitstreams up to cognitive deepfake neural classification."
        },
        # Slide 5: Complete Frame Extraction Engine
        {
            "title": "100% Decoded Frame Extraction Guarantee",
            "subtitle": "Zero Subsampling: Eliminating Temporal Splice Blindspots",
            "category": "CORE INNOVATION #1",
            "bullets": [
                "No Skipping or Downsampling: A 60-second 30 FPS video yields exactly 1,800 decoded frames.",
                "High-Throughput Streaming: Memory-efficient OpenCV/FFmpeg batch decompression without OOM crashes.",
                "Cryptographic Integrity: Every single extracted frame receives a SHA-256 hash and unique frame ID.",
                "Timestamp Precision: Millisecond-accurate timestamping (HH:MM:SS.mmm) for forensic audit trails.",
                "Fail-Closed Accounting: System verifies that extracted_frames == total_decoded_frames before permitting evaluation. Corrupt decodes immediately route to BLOCK."
            ],
            "notes": "This is one of our primary innovations. We do not merely inspect a couple of keyframes. We decode and extract every individual frame, calculating cryptographic fingerprints for each."
        },
        # Slide 6: Dual-Engine AI Frame Classification
        {
            "title": "Dual-Engine AI Frame Classification",
            "subtitle": "Combining Neural Frequency Artifacts with Optical Physics",
            "category": "CORE INNOVATION #2",
            "bullets": [
                "1. PyTorch Convolutional Frequency Classifier: Evaluates high-frequency spectral residuals where generative diffusion and GAN models leave synthetic boundary artifacts.",
                "2. Compression Residual Error (MSE): Spliced deepfake faces alter local quantization tables, producing abnormal recompression mean-squared error spikes.",
                "3. Laplacian Edge Sharpness Variance: Evaluates focal dispersion across frames to distinguish natural camera lens physics from synthetic Gaussian smoothing.",
                "4. Inter-Frame Color Histogram Correlation: Tracks RGB/HSV distribution shifts to detect temporal flicker across facial bounding boxes.",
                "5. Fail-Closed Error Isolation: If neural inference fails or times out, the frame is marked UNCERTAIN and the video is quarantined."
            ],
            "notes": "A single model cannot catch every deepfake. We use a dual-engine paradigm: a PyTorch deep learning convolutional neural network paired with physical forensic heuristics."
        },
        # Slide 7: Visual Color Taxonomy
        {
            "title": "Frame Color Classification Convention",
            "subtitle": "Intuitive Security Mapping: Green for Safe, Red for Morphed / Bad Content",
            "category": "STANDARDS & CONVENTIONS",
            "bullets": [
                "GREEN - Safe / Legitimate / Authentic Frame (#22c55e): Natural camera capture, coherent CMOS sensor noise, consistent edge sharpness. Post approved to publish.",
                "RED - Morphed / Suspicious / AI-Manipulated / Bad Content (#ef4444): Deepfake facial artifacts, abnormal compression residuals, temporal discontinuities, sexual or bad content. Post blocked and quarantined.",
                "YELLOW - Uncertain Frame (#eab308): Underexposed frames, heavy motion blur, or inconclusive AI confidence. System verdict: Ambiguous / Fail-Closed.",
                "Visual Stamping: Every extracted frame thumbnail is dynamically stamped with a colored border, uppercase status pill, frame number, and timestamp.",
                "Intuitive Semantics: Green represents authentic, safe media; Red alerts to morphed, manipulated, or prohibited violations."
            ],
            "notes": "Our color mapping enforces intuitive security semantics: GREEN indicates Safe, authentic videos; RED signifies Morphed, manipulated, deepfake, or bad content; and YELLOW represents Uncertain."
        },
        # Slide 8: Video Risk Assessment & Policy Engine
        {
            "title": "Composite Video Risk Assessment & Policy",
            "subtitle": "Mathematically Rigorous 0 to 100 Scoring Model",
            "category": "DECISION ENGINE",
            "bullets": [
                "Risk Score Formulation: Risk = min(100, (Suspicious_Ratio * 85) + (Uncertain_Ratio * 35) + Max_Anomaly * 20)",
                "Policy Thresholds:",
                "  - ALLOW (0 <= Risk < 15): 100% of frames are GREEN (Safe). Zero morphed or uncertain frames. Media published to website feed.",
                "  - QUARANTINE (15 <= Risk <= 100): At least 1 frame is RED (Morphed/Bad) or YELLOW (Uncertain). Media held in isolated quarantine for SOC review.",
                "  - BLOCK: File contains prohibited cryptographic signature, corrupted container bitstream, or explicit banned content. File purged immediately.",
                "Zero Tolerance: Public users can never access or stream quarantined videos."
            ],
            "notes": "Our composite risk engine combines ratios of suspicious and uncertain frames with peak anomaly scores. Even a single tampered frame immediately locks the video in quarantine."
        },
        # Slide 9: Instagram Web Interface & In-Line Firewall
        {
            "title": "Instagram Application Interface & Any-App SDK",
            "subtitle": "SafeGate Running Seamlessly in the Background of Real Web Apps",
            "category": "FULL-STACK IMPLEMENTATION",
            "bullets": [
                "Realistic Instagram Web Interface: High-fidelity Instagram UI with Stories tray, Reels feed, and Create Post/Reel modal.",
                "Background Firewall Operation: When the user clicks 'Share', SafeGate intercepts and screens the video in the background without needing a separate upload site.",
                "In-Line Verification Feedback: Real-time screening sheet displays extraction progress, PyTorch analysis, and post verification.",
                "Zero-Trust Gating: Safe videos (GREEN) are published immediately to the Instagram feed; morphed videos (RED) trigger an in-app security alert and are blocked.",
                "Any-App Integration SDK: Can be included in any web or mobile application (Instagram, TikTok, banking video KYC, news portals) with a 3-line middleware snippet."
            ],
            "notes": "SafeGate is not just another upload site. We built an authentic Instagram interface where SafeGate operates in the background as an in-line middleware, proving how it can be integrated into any web application."
        },
        # Slide 10: Real-Time Scanning & Interactive Gallery
        {
            "title": "Interactive Frame Inspection Gallery",
            "subtitle": "Deep Forensic Inspection with Side-by-Side Comparison",
            "category": "INVESTIGATIVE TOOLING",
            "bullets": [
                "Dynamic Gallery Grid: Paginated display of all decoded frames with colored borders and classification badges.",
                "Filter Chips: Instant switching between All Frames, 🔴 Legitimate, 🟢 Suspicious/AI, and 🟡 Uncertain.",
                "Lightbox Frame Modal: Click any frame to view full resolution with deep forensic metadata.",
                "Adjacent Frame Comparison: Side-by-side display of Previous Frame, Current Frame, and Next Frame to visually verify splice transitions.",
                "Next Suspicious Scrubber: Instant navigation jump directly to the next suspicious frame in the timeline."
            ],
            "notes": "Administrators can inspect every single extracted frame in the gallery, compare neighboring frames side-by-side, and verify why the AI flagged the frame."
        },
        # Slide 11: Video Frame Timeline & Suspicious Segments
        {
            "title": "Interactive Timeline & Segment Clustering",
            "subtitle": "Temporal Mapping of Discontinuities Across the Stream",
            "category": "TEMPORAL ANALYSIS",
            "bullets": [
                "Color-Coded Scrubber Bar: Visualizes the entire video duration with color-coded ticks (Red, Green, Yellow).",
                "Instant Jump: Clicking any marker scrubs directly to the corresponding frame and timestamp.",
                "Automated Segment Grouping: Contiguous runs of suspicious frames are aggregated into distinct Suspicious Segments.",
                "Segment Telemetry: Displays start/end frame numbers, millisecond time boundaries, and duration.",
                "Example Detection: Identifies 'Segment #1: Frames 25-25 (00:00:01.042 - 00:00:01.042) - Duration: 0.04s - High JPEG MSE Anomaly'."
            ],
            "notes": "The video timeline maps out every frame across time and automatically clusters consecutive flagged frames into suspicious segments."
        },
        # Slide 12: SOC Moderation & Tamper-Evident Audit Ledger
        {
            "title": "Security Operations Center (SOC) Console",
            "subtitle": "Active Quarantine Management & Cryptographic Audit Trail",
            "category": "OPERATIONAL SECURITY",
            "bullets": [
                "Executive Metrics & Charts: Real-time telemetry powered by Chart.js displaying firewall decisions and frame distributions.",
                "Quarantine Moderation Queue: Human-in-the-loop interface allowing authorized analysts to Approve (Publish) or Reject (Destroy) videos.",
                "Tamper-Evident Audit Ledger: Every scan, verdict, and moderation override is hashed into a sequential HMAC SHA-256 chain.",
                "Hash-Chaining Formula: Row[i] = SHA256(Row[i-1] + Action + UploadID + Timestamp).",
                "1-Click Integrity Verification: 'Verify Hash Chain Integrity' button scans database rows to cryptographically guarantee zero tampering."
            ],
            "notes": "Our SOC console provides moderation workflows backed by an immutable SHA-256 HMAC audit ledger where past records cannot be altered without breaking the hash chain."
        },
        # Slide 13: 6 Demonstration Scenarios Evaluation
        {
            "title": "Experimental Validation: 6 Test Scenarios",
            "subtitle": "Comprehensive Benchmark Across Realistic Attack Vectors",
            "category": "EMPIRICAL RESULTS",
            "bullets": [
                "Scenario 1: Authentic Video -> 100% GREEN frames (Safe) -> Risk: 0/100 -> ALLOW (Published to Instagram feed).",
                "Scenario 2: Deepfake Video -> 45 RED frames (Morphed/Bad) -> Risk: 92/100 -> QUARANTINE (Blocked with security alert).",
                "Scenario 3: Single-Frame Tamper -> Exactly Frame #25 marked RED, 44 others GREEN -> QUARANTINE (Pinpoint caught).",
                "Scenario 4: Uncertain Clarity -> Low contrast / blur marked YELLOW -> Risk: 50/100 -> QUARANTINE (Fail-closed).",
                "Scenario 5: Corrupted Stream -> Invalid container bitstream -> BLOCK (Rejected and purged).",
                "Scenario 6: AI Model Failure -> Simulated inference exception -> QUARANTINE (Refuses to fail open)."
            ],
            "notes": "We implemented a 1-click test launcher for 6 real-world scenarios. Notably in Scenario 3, SafeGate successfully pinpoints a single tampered frame at Frame 25 amid 44 authentic frames."
        },
        # Slide 14: Automated Testing & Verification
        {
            "title": "Automated Testing & Code Quality Suite",
            "subtitle": "74 Automated Unit, Integration, and Security Tests Passing",
            "category": "VERIFICATION & QUALITY",
            "bullets": [
                "100% Pass Rate: 74 out of 74 automated tests passing across 10 test suites.",
                "Legacy Stack Preservation: All 60 legacy 7-layer OSI tests continue to pass with 0 regressions.",
                "SafeGate 2.0 Test Suite (tests/test_safegate2.py): 14 comprehensive end-to-end integration tests.",
                "Tested Scenarios: File ingestion, 100% frame extraction, PyTorch classifier inference, color mapping, timeline generation, quarantine workflow, and website stream gating.",
                "Security Hardening: Tested against path traversal, oversized payloads, invalid MIME types, and rate limiting."
            ],
            "notes": "We enforce rigorous software engineering standards: 74 automated tests pass in under 15 seconds, verifying complete backward compatibility and robust security."
        },
        # Slide 15: Comparative Analysis & Industrial Relevance
        {
            "title": "Comparative Analysis: SafeGate vs Industry",
            "subtitle": "Why In-Line Frame Firewalls Are the Future of Media Security",
            "category": "INDUSTRY IMPACT",
            "bullets": [
                "Traditional WAFs (Cloudflare/AWS): Network-only; No multimedia inspection; Blind to deepfakes.",
                "Static Media Scanners: Inspect 1-2 frames/sec; High single-frame bypass rate; Post-upload only.",
                "SafeGate 2.0: 100% Decoded Frame Extraction; Dual-engine AI; In-line zero-trust publishing gating; SHA-256 HMAC ledger.",
                "Societal Impact: Protects elections, corporate executive impersonation, and public forums against weaponized disinformation.",
                "Deployment Flexibility: Self-hosted Docker container, sub-second API response, zero cloud vendor lock-in."
            ],
            "notes": "Compared to commercial alternatives, SafeGate 2.0 provides true in-line protection, full frame decoding, and an immutable cryptographic audit trail."
        },
        # Slide 16: Conclusion & Future Enhancements
        {
            "title": "Conclusion & Future Research Directions",
            "subtitle": "Summary of Deliverables & Project Contributions",
            "category": "CONCLUSION",
            "bullets": [
                "Key Contributions: In-line video firewall, 100% complete frame extraction, dual-engine AI classification, strict inverted color convention, and zero-trust website integration.",
                "Academic Deliverables: Working code on GitHub, full demo web application, A1 poster, video demonstration, and 60+ page capstone report.",
                "Future Directions:",
                "  - Integration of audio-visual multimodal deepfake detection (wav2lip / voice cloning).",
                "  - Hardware acceleration via NVIDIA TensorRT for 4K 60FPS real-time enterprise streaming.",
                "  - Decentralized ledger anchoring using Ethereum/Polygon for multi-organization trust federation.",
                "Thank You! Questions & Discussion Welcomed from the Panel."
            ],
            "notes": "In conclusion, SafeGate 2.0 demonstrates that frame-level deepfake firewalling is technically feasible and essential. Thank you, and I look forward to your questions."
        }
    ]

    for idx, data in enumerate(slides_data):
        slide = prs.slides.add_slide(blank_layout)

        # Background rectangle
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = c_bg
        bg.line.fill.background()

        # Top Category pill
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.4))
        cat_tf = cat_box.text_frame
        cat_tf.word_wrap = True
        p_cat = cat_tf.paragraphs[0]
        p_cat.text = data["category"]
        p_cat.font.name = "Arial"
        p_cat.font.size = Pt(11)
        p_cat.font.bold = True
        p_cat.font.color.rgb = c_cyan

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.7), Inches(0.8))
        title_tf = title_box.text_frame
        title_tf.word_wrap = True
        p_title = title_tf.paragraphs[0]
        p_title.text = data["title"]
        p_title.font.name = "Arial"
        p_title.font.size = Pt(24)
        p_title.font.bold = True
        p_title.font.color.rgb = c_white

        # Subtitle
        sub_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.7), Inches(0.5))
        sub_tf = sub_box.text_frame
        sub_tf.word_wrap = True
        p_sub = sub_tf.paragraphs[0]
        p_sub.text = data["subtitle"]
        p_sub.font.name = "Arial"
        p_sub.font.size = Pt(14)
        p_sub.font.italic = True
        p_sub.font.color.rgb = c_muted

        # Main Content Card
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.1), Inches(11.7), Inches(4.7))
        card.fill.solid()
        card.fill.fore_color.rgb = c_card
        card.line.color.rgb = RGBColor(40, 50, 80)
        card.line.width = Pt(1.5)

        # Bullets inside card
        tb = slide.shapes.add_textbox(Inches(1.1), Inches(2.3), Inches(11.1), Inches(4.3))
        tf = tb.text_frame
        tf.word_wrap = True

        for b_idx, bullet in enumerate(data["bullets"]):
            p = tf.add_paragraph() if b_idx > 0 else tf.paragraphs[0]
            p.text = "•  " + bullet
            p.font.name = "Arial"
            p.font.size = Pt(14)
            p.font.color.rgb = c_white
            p.space_after = Pt(10)

            # Highlight keywords if present
            if "RED" in bullet:
                p.font.color.rgb = c_red
            elif "GREEN" in bullet:
                p.font.color.rgb = c_green
            elif "YELLOW" in bullet:
                p.font.color.rgb = c_yellow

        # Footer: Slide Number & University
        ft_box = slide.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(11.7), Inches(0.4))
        ft_tf = ft_box.text_frame
        p_ft = ft_tf.paragraphs[0]
        p_ft.text = f"SR University | School of CS&AI | Slide {idx + 1} of {len(slides_data)} | SafeGate 2.0 Capstone Defense"
        p_ft.font.name = "Arial"
        p_ft.font.size = Pt(9)
        p_ft.font.color.rgb = c_muted

        # Speaker Notes
        notes_slide = slide.notes_slide
        tf_notes = notes_slide.notes_text_frame
        tf_notes.text = data["notes"]

    out_path = os.path.join("submission", "2103A52001-Bongoni_Devendar_Goud_Presentation.pptx")
    prs.save(out_path)
    print(f"[+] Successfully generated presentation: {out_path} ({len(slides_data)} slides)")

if __name__ == "__main__":
    create_presentation()
