"""
SafeGate — Automated Demo Video Generator
=========================================
Generates a complete, high-definition (1920x1080 @ 30fps) animated MP4 demo video
showcasing the SafeGate 7-Layer OSI Security Architecture and live screening:

SCENES:
1. Title & Architectural Introduction (SafeGate Fail-Closed AI Upload Gateway).
2. The 7-Layer OSI Model breakdown (Physical, Data Link, Network, Transport, Session, Presentation, Application).
3. Live Simulation 1: Clean Media Screening -> Layer-by-Layer Verification -> VERDICT: ALLOW (Published).
4. Live Simulation 2: Prohibited Media Detection -> Layer 4 Checksum Match -> VERDICT: BLOCK (Deleted & Blocklisted).
5. Live Simulation 3: Cryptographic SHA-256 Audit Chain Verification -> Integrity Intact.
6. Summary & Defense Readiness.
"""

from pathlib import Path
import cv2
import numpy as np

OUTPUT_FILE = Path(__file__).resolve().parent / "safegate_demo.mp4"
WIDTH = 1920
HEIGHT = 1080
FPS = 30

# Colors (BGR format for OpenCV)
BG_COLOR = (23, 14, 10)         # Deep dark blue #0a0e17
PANEL_COLOR = (52, 34, 24)      # Dark slate card #182234
BORDER_COLOR = (74, 50, 36)     # Border #24324a
TEXT_WHITE = (240, 244, 248)
TEXT_MUTED = (184, 163, 148)
TEXT_DIM = (139, 116, 100)
CYAN = (248, 189, 56)           # #38bdf8 in BGR
GREEN = (129, 185, 16)          # #10b981 in BGR
AMBER = (11, 158, 245)          # #f59e0b in BGR
RED = (68, 68, 239)             # #ef4444 in BGR


def create_canvas():
    """Returns a fresh 1080p canvas with background styling."""
    canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    canvas[:] = BG_COLOR
    # Add subtle top banner line
    cv2.line(canvas, (0, 0), (WIDTH, 0), CYAN, 4)
    return canvas


def draw_header(canvas, subtitle="7-Layer OSI Security Screening Gateway"):
    cv2.putText(canvas, "SafeGate", (80, 70), cv2.FONT_HERSHEY_DUPLEX, 1.4, TEXT_WHITE, 2, cv2.LINE_AA)
    cv2.putText(canvas, "|", (280, 68), cv2.FONT_HERSHEY_DUPLEX, 1.2, TEXT_DIM, 1, cv2.LINE_AA)
    cv2.putText(canvas, subtitle, (310, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.85, CYAN, 2, cv2.LINE_AA)
    cv2.line(canvas, (80, 95), (WIDTH - 80, 95), BORDER_COLOR, 1)


def render_scene_title(writer):
    """Scene 1: Introduction Title Card (4 seconds)."""
    frames = 4 * FPS
    for f in range(frames):
        canvas = create_canvas()
        draw_header(canvas, "Project Defense & System Demonstration")

        # Central Shield / Badge Box
        cv2.rectangle(canvas, (460, 260), (1460, 820), PANEL_COLOR, -1)
        cv2.rectangle(canvas, (460, 260), (1460, 820), CYAN, 2)

        # Title text
        cv2.putText(canvas, "SAFEGATE", (680, 390), cv2.FONT_HERSHEY_DUPLEX, 2.2, TEXT_WHITE, 3, cv2.LINE_AA)
        cv2.putText(canvas, "Self-Hosted Fail-Closed AI Upload Gateway", (530, 460), cv2.FONT_HERSHEY_SIMPLEX, 1.1, CYAN, 2, cv2.LINE_AA)
        
        cv2.line(canvas, (560, 500), (1360, 500), BORDER_COLOR, 1)

        features = [
            "- 7-Layer OSI Protocol Stack Architecture (Layers 1-7)",
            "- Fail-Closed Defensive Engineering (Zero Bypass on Failure)",
            "- Local Vision Transformer + Gemini Multimodal Second Opinion",
            "- Cryptographic SHA-256 Tamper-Evident Hash Chain Audit Log",
            "- Standalone CLI Security Appliance & Headless Protocol Daemon"
        ]
        y = 560
        for item in features:
            cv2.putText(canvas, item, (540, y), cv2.FONT_HERSHEY_SIMPLEX, 0.72, TEXT_MUTED, 1, cv2.LINE_AA)
            y += 44

        cv2.putText(canvas, "STATUS: OPERATIONAL | 60/60 UNIT TESTS PASSED", (630, 785), cv2.FONT_HERSHEY_SIMPLEX, 0.75, GREEN, 2, cv2.LINE_AA)
        writer.write(canvas)


def render_scene_osi_overview(writer):
    """Scene 2: 7-Layer OSI Model Architecture (5 seconds)."""
    layers = [
        ("Layer 7", "Application", "AI Policy Gate, Falconsai Vision Transformer, Gemini Opinion, Deepfake Scoring"),
        ("Layer 6", "Presentation", "Magic-Byte Syntax Validation, RGB Transcoding, 64-bit DCT pHash Deduplication"),
        ("Layer 5", "Session", "Constant-Time Authentication (hmac.compare_digest), SHA-256 Audit Hash Chain"),
        ("Layer 4", "Transport", "End-to-End SHA-256 Cryptographic Checksum & O(1) Exact Blocklist Lookup"),
        ("Layer 3", "Network", "Client IP Origin Resolution, Sliding-Window Rate Limiting (10 req/min)"),
        ("Layer 2", "Data Link", "Video Frame Delineation, Temporal Interval Sampling, Max Frames Capping"),
        ("Layer 1", "Physical", "Chunked Bitstream Ingestion (64KB), Zero-Trust File Size Boundaries (200MB)")
    ]

    total_frames = 5 * FPS
    for f in range(total_frames):
        canvas = create_canvas()
        draw_header(canvas, "OSI Protocol Stack Model Architecture")

        cv2.putText(canvas, "7-LAYER DEFENSIVE PROTOCOL STACK", (100, 160), cv2.FONT_HERSHEY_DUPLEX, 1.1, TEXT_WHITE, 2, cv2.LINE_AA)
        cv2.putText(canvas, "Every incoming media stream traverses all 7 layers sequentially before publication.", (100, 195), cv2.FONT_HERSHEY_SIMPLEX, 0.75, TEXT_MUTED, 1, cv2.LINE_AA)

        y = 250
        for l_num, name, desc in layers:
            # Highlight layers with alternate color accents
            accent = CYAN if "7" in l_num or "4" in l_num or "5" in l_num else GREEN
            
            # Layer Box
            cv2.rectangle(canvas, (100, y - 30), (1820, y + 42), PANEL_COLOR, -1)
            cv2.rectangle(canvas, (100, y - 30), (1820, y + 42), BORDER_COLOR, 1)

            cv2.putText(canvas, l_num, (125, y + 14), cv2.FONT_HERSHEY_DUPLEX, 0.85, accent, 2, cv2.LINE_AA)
            cv2.putText(canvas, name.upper(), (290, y + 14), cv2.FONT_HERSHEY_DUPLEX, 0.85, TEXT_WHITE, 2, cv2.LINE_AA)
            cv2.putText(canvas, desc, (620, y + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.65, TEXT_MUTED, 1, cv2.LINE_AA)

            y += 85

        writer.write(canvas)


def render_scene_scan_clean(writer):
    """Scene 3: Live Clean Scan Execution -> ALLOW (6 seconds)."""
    steps = [
        ("Layer 5", "Session (Authentication)", "PASS", "0.0ms", "Session authenticated for role 'client'."),
        ("Layer 3", "Network (Traffic Policing)", "PASS", "0.0ms", "IP 127.0.0.1 traffic conforms to policy (1/10)."),
        ("Layer 1", "Physical (Bitstream Ingestion)", "PASS", "0.2ms", "Stream buffered safely (53,855 bytes)."),
        ("Layer 6", "Presentation (Syntax Validation)", "PASS", "3.4ms", "MIME format confirmed: video/mp4 (.mp4)."),
        ("Layer 4", "Transport (Integrity Checksum)", "PASS", "8.7ms", "SHA-256 clean: d0be492050488172..."),
        ("Layer 2", "Data Link (Temporal Framing)", "PASS", "66.2ms", "Extracted 3 synchronized frames."),
        ("Layer 6", "Presentation (pHash Deduplication)", "PASS", "719.5ms", "Computed 3 frame pHashes. Blocklist clean."),
        ("Layer 7", "Application (Cognitive Policy)", "ALLOW", "102.4ms", "NSFW: 0.02, Deepfake: 10/100 -> ALLOW")
    ]

    total_frames = 6 * FPS
    for f in range(total_frames):
        canvas = create_canvas()
        draw_header(canvas, "Live CLI Execution: Clean Media Ingestion")

        # Command terminal prompt box
        cv2.rectangle(canvas, (100, 130), (1820, 190), (15, 10, 8), -1)
        cv2.rectangle(canvas, (100, 130), (1820, 190), BORDER_COLOR, 1)
        cv2.putText(canvas, "$ python cli.py scan sample_clean.mp4", (125, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 120), 2, cv2.LINE_AA)

        # Step progression based on frame count
        visible_steps = min(len(steps), int((f / FPS) * 1.8) + 1)

        # Table Header
        cv2.rectangle(canvas, (100, 215), (1820, 260), (35, 25, 18), -1)
        cv2.putText(canvas, "LAYER", (125, 245), cv2.FONT_HERSHEY_DUPLEX, 0.7, TEXT_DIM, 1, cv2.LINE_AA)
        cv2.putText(canvas, "SUBSYSTEM", (320, 245), cv2.FONT_HERSHEY_DUPLEX, 0.7, TEXT_DIM, 1, cv2.LINE_AA)
        cv2.putText(canvas, "STATUS", (860, 245), cv2.FONT_HERSHEY_DUPLEX, 0.7, TEXT_DIM, 1, cv2.LINE_AA)
        cv2.putText(canvas, "LATENCY", (1040, 245), cv2.FONT_HERSHEY_DUPLEX, 0.7, TEXT_DIM, 1, cv2.LINE_AA)
        cv2.putText(canvas, "OPERATIONAL DETAILS", (1220, 245), cv2.FONT_HERSHEY_DUPLEX, 0.7, TEXT_DIM, 1, cv2.LINE_AA)

        y = 300
        for i in range(visible_steps):
            layer, sub, status, lat, details = steps[i]
            cv2.rectangle(canvas, (100, y - 22), (1820, y + 26), PANEL_COLOR, -1)
            cv2.rectangle(canvas, (100, y - 22), (1820, y + 26), BORDER_COLOR, 1)

            cv2.putText(canvas, layer, (125, y + 8), cv2.FONT_HERSHEY_DUPLEX, 0.7, CYAN, 1, cv2.LINE_AA)
            cv2.putText(canvas, sub, (320, y + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, TEXT_WHITE, 2, cv2.LINE_AA)
            cv2.putText(canvas, status, (860, y + 8), cv2.FONT_HERSHEY_DUPLEX, 0.75, GREEN, 2, cv2.LINE_AA)
            cv2.putText(canvas, lat, (1040, y + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.65, TEXT_MUTED, 1, cv2.LINE_AA)
            cv2.putText(canvas, details, (1220, y + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.65, TEXT_MUTED, 1, cv2.LINE_AA)
            y += 58

        # Verdict Badge when complete
        if visible_steps >= len(steps):
            cv2.rectangle(canvas, (100, 780), (1820, 1000), (28, 48, 20), -1)
            cv2.rectangle(canvas, (100, 780), (1820, 1000), GREEN, 2)

            cv2.putText(canvas, ">>> FINAL VERDICT: ALLOW (PUBLISHED) <<<", (135, 835), cv2.FONT_HERSHEY_DUPLEX, 1.25, GREEN, 2, cv2.LINE_AA)
            cv2.putText(canvas, "Upload ID: 14382f200dc844fbb0f31902c16ff846", (135, 885), cv2.FONT_HERSHEY_SIMPLEX, 0.75, TEXT_WHITE, 1, cv2.LINE_AA)
            cv2.putText(canvas, "SHA-256: d0be4920504881722653251bb916fd116bdcb7244f67a1db22c112feef2a11b9", (135, 920), cv2.FONT_HERSHEY_SIMPLEX, 0.72, TEXT_MUTED, 1, cv2.LINE_AA)
            cv2.putText(canvas, "NSFW Peak: 2.0%  |  Deepfake Risk: 10/100 (Safe)  |  Pipeline Latency: 0.903s", (135, 960), cv2.FONT_HERSHEY_SIMPLEX, 0.75, CYAN, 2, cv2.LINE_AA)

        writer.write(canvas)


def render_scene_scan_block(writer):
    """Scene 4: Live Prohibited Media Detection -> Immediate BLOCK at Layer 4 (5 seconds)."""
    total_frames = 5 * FPS
    for f in range(total_frames):
        canvas = create_canvas()
        draw_header(canvas, "Defense-in-Depth: Early Termination on Blocklist Hit")

        cv2.rectangle(canvas, (100, 130), (1820, 190), (15, 10, 8), -1)
        cv2.rectangle(canvas, (100, 130), (1820, 190), BORDER_COLOR, 1)
        cv2.putText(canvas, "$ python cli.py scan sample_blocked.mp4", (125, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 120), 2, cv2.LINE_AA)

        steps = [
            ("Layer 5", "Session (Authentication)", "PASS", "0.0ms", "Session authenticated for role 'client'."),
            ("Layer 3", "Network (Traffic Policing)", "PASS", "0.0ms", "IP 127.0.0.1 conforms to rate policy."),
            ("Layer 1", "Physical (Bitstream Ingestion)", "PASS", "0.1ms", "Stream buffered safely."),
            ("Layer 6", "Presentation (Syntax Validation)", "PASS", "2.0ms", "MIME format confirmed: video/mp4."),
            ("Layer 4", "Transport (Integrity Checksum)", "BLOCKED", "7.4ms", "[Layer 4 Violation] Checksum matched exact blocklist!")
        ]

        # Table Header
        cv2.rectangle(canvas, (100, 215), (1820, 260), (35, 25, 18), -1)
        cv2.putText(canvas, "LAYER", (125, 245), cv2.FONT_HERSHEY_DUPLEX, 0.7, TEXT_DIM, 1, cv2.LINE_AA)
        cv2.putText(canvas, "SUBSYSTEM", (320, 245), cv2.FONT_HERSHEY_DUPLEX, 0.7, TEXT_DIM, 1, cv2.LINE_AA)
        cv2.putText(canvas, "STATUS", (860, 245), cv2.FONT_HERSHEY_DUPLEX, 0.7, TEXT_DIM, 1, cv2.LINE_AA)
        cv2.putText(canvas, "LATENCY", (1040, 245), cv2.FONT_HERSHEY_DUPLEX, 0.7, TEXT_DIM, 1, cv2.LINE_AA)
        cv2.putText(canvas, "OPERATIONAL DETAILS", (1220, 245), cv2.FONT_HERSHEY_DUPLEX, 0.7, TEXT_DIM, 1, cv2.LINE_AA)

        y = 300
        for layer, sub, status, lat, details in steps:
            cv2.rectangle(canvas, (100, y - 22), (1820, y + 26), PANEL_COLOR, -1)
            cv2.rectangle(canvas, (100, y - 22), (1820, y + 26), BORDER_COLOR, 1)

            st_color = RED if status == "BLOCKED" else GREEN
            cv2.putText(canvas, layer, (125, y + 8), cv2.FONT_HERSHEY_DUPLEX, 0.7, CYAN, 1, cv2.LINE_AA)
            cv2.putText(canvas, sub, (320, y + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, TEXT_WHITE, 2, cv2.LINE_AA)
            cv2.putText(canvas, status, (860, y + 8), cv2.FONT_HERSHEY_DUPLEX, 0.75, st_color, 2, cv2.LINE_AA)
            cv2.putText(canvas, lat, (1040, y + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.65, TEXT_MUTED, 1, cv2.LINE_AA)
            cv2.putText(canvas, details, (1220, y + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.65, st_color if status == "BLOCKED" else TEXT_MUTED, 1, cv2.LINE_AA)
            y += 58

        # Red Block Box
        cv2.rectangle(canvas, (100, 630), (1820, 960), (25, 20, 50), -1)
        cv2.rectangle(canvas, (100, 630), (1820, 960), RED, 2)

        cv2.putText(canvas, ">>> FINAL VERDICT: BLOCK (DELETED & BLOCKLISTED) <<<", (135, 695), cv2.FONT_HERSHEY_DUPLEX, 1.25, RED, 2, cv2.LINE_AA)
        cv2.putText(canvas, "DEFENSIVE ACTION: Quarantined payload deleted immediately from disk (Zero Storage Policy).", (135, 750), cv2.FONT_HERSHEY_SIMPLEX, 0.8, TEXT_WHITE, 1, cv2.LINE_AA)
        cv2.putText(canvas, "PIPELINE TERMINATION TIME: 7.4 milliseconds (Saved CPU/GPU by avoiding higher-layer decoding).", (135, 795), cv2.FONT_HERSHEY_SIMPLEX, 0.8, CYAN, 2, cv2.LINE_AA)
        cv2.putText(canvas, "REASON: Cryptographic transport checksum matches known prohibited media database.", (135, 840), cv2.FONT_HERSHEY_SIMPLEX, 0.75, TEXT_MUTED, 1, cv2.LINE_AA)
        cv2.putText(canvas, "AUDIT LOG: Cryptographic checkpoint committed to tamper-evident SHA-256 chain.", (135, 885), cv2.FONT_HERSHEY_SIMPLEX, 0.75, TEXT_MUTED, 1, cv2.LINE_AA)

        writer.write(canvas)


def render_scene_audit_verify(writer):
    """Scene 5: Cryptographic Audit Chain Verification (4 seconds)."""
    total_frames = 4 * FPS
    for f in range(total_frames):
        canvas = create_canvas()
        draw_header(canvas, "Cryptographic Audit Log Verification")

        cv2.rectangle(canvas, (100, 130), (1820, 190), (15, 10, 8), -1)
        cv2.rectangle(canvas, (100, 130), (1820, 190), BORDER_COLOR, 1)
        cv2.putText(canvas, "$ python cli.py audit", (125, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 120), 2, cv2.LINE_AA)

        # Audit Integrity Box
        cv2.rectangle(canvas, (100, 230), (1820, 780), PANEL_COLOR, -1)
        cv2.rectangle(canvas, (100, 230), (1820, 780), GREEN, 2)

        cv2.putText(canvas, "VERIFYING CRYPTOGRAPHIC SHA-256 HASH CHAIN...", (140, 290), cv2.FONT_HERSHEY_DUPLEX, 1.0, TEXT_WHITE, 2, cv2.LINE_AA)
        cv2.line(canvas, (140, 315), (1780, 315), BORDER_COLOR, 1)

        cv2.putText(canvas, "[+] AUDIT INTEGRITY: VALID (CRYPTOGRAPHIC CHAIN INTACT)", (140, 375), cv2.FONT_HERSHEY_DUPLEX, 1.25, GREEN, 2, cv2.LINE_AA)
        
        cv2.putText(canvas, "Algorithm: row_hash[i] = SHA256( row_hash[i-1] + action + details + upload_id + timestamp )", (140, 440), cv2.FONT_HERSHEY_SIMPLEX, 0.8, CYAN, 2, cv2.LINE_AA)
        cv2.putText(canvas, "- Genesis Block Hash:  0000000000000000000000000000000000000000000000000000000000000000", (140, 495), cv2.FONT_HERSHEY_SIMPLEX, 0.72, TEXT_MUTED, 1, cv2.LINE_AA)
        cv2.putText(canvas, "- Total Sequential Entries Verified: 7 records", (140, 545), cv2.FONT_HERSHEY_SIMPLEX, 0.8, TEXT_WHITE, 1, cv2.LINE_AA)
        cv2.putText(canvas, "- Detected Breakage Point: None (Zero unauthorized modifications or deleted rows)", (140, 595), cv2.FONT_HERSHEY_SIMPLEX, 0.8, TEXT_WHITE, 1, cv2.LINE_AA)
        cv2.putText(canvas, "- Status: Mathematical integrity verified from genesis to chain tip.", (140, 645), cv2.FONT_HERSHEY_SIMPLEX, 0.8, GREEN, 2, cv2.LINE_AA)

        cv2.putText(canvas, "TAMPER-RESISTANT ASSURANCE: Retrospective SQL tampering is immediately flagged.", (140, 720), cv2.FONT_HERSHEY_SIMPLEX, 0.75, TEXT_MUTED, 1, cv2.LINE_AA)

        writer.write(canvas)


def render_scene_summary(writer):
    """Scene 6: Conclusion & Viva Readiness (4 seconds)."""
    total_frames = 4 * FPS
    for f in range(total_frames):
        canvas = create_canvas()
        draw_header(canvas, "Final-Year Mini Project Summary")

        cv2.rectangle(canvas, (400, 220), (1520, 840), PANEL_COLOR, -1)
        cv2.rectangle(canvas, (400, 220), (1520, 840), CYAN, 2)

        cv2.putText(canvas, "PROJECT COMPLETE & OPERATIONAL", (540, 310), cv2.FONT_HERSHEY_DUPLEX, 1.4, TEXT_WHITE, 2, cv2.LINE_AA)
        cv2.line(canvas, (480, 345), (1440, 345), BORDER_COLOR, 1)

        items = [
            ("Core Engineering:", "7-Layer OSI Protocol Stack for Media Security"),
            ("Fail-Closed Design:", "All anomalies route to REVIEW or BLOCK; never ALLOW"),
            ("AI Vision Defense:", "Hugging Face ViT + Gemini Multimodal Second Opinion"),
            ("Digital Forensics:", "Laplacian sharpness variance, temporal color flicker & metadata"),
            ("Integrity Logging:", "Sequential SHA-256 cryptographic blockchain-style audit log"),
            ("CLI & Network Daemon:", "cli.py tool + headless protocol server with protocol headers"),
            ("Verification Suite:", "60 Unit & Integration Tests (100% Pass Rate)")
        ]

        y = 405
        for heading, val in items:
            cv2.putText(canvas, heading, (460, y), cv2.FONT_HERSHEY_DUPLEX, 0.72, CYAN, 1, cv2.LINE_AA)
            cv2.putText(canvas, val, (770, y), cv2.FONT_HERSHEY_SIMPLEX, 0.72, TEXT_WHITE, 1, cv2.LINE_AA)
            y += 52

        cv2.putText(canvas, "Ready for University Viva Voce Examination & Defense", (580, 795), cv2.FONT_HERSHEY_SIMPLEX, 0.85, GREEN, 2, cv2.LINE_AA)

        writer.write(canvas)


def generate_full_demo():
    print(f"Generating SafeGate demonstration video at: {OUTPUT_FILE} ...")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(OUTPUT_FILE), fourcc, FPS, (WIDTH, HEIGHT))

    if not writer.isOpened():
        raise RuntimeError("Failed to open OpenCV VideoWriter for MP4 creation.")

    print("Rendering Scene 1: Introduction Title...")
    render_scene_title(writer)

    print("Rendering Scene 2: 7-Layer OSI Model Overview...")
    render_scene_osi_overview(writer)

    print("Rendering Scene 3: Clean Media Screening (ALLOW)...")
    render_scene_scan_clean(writer)

    print("Rendering Scene 4: Prohibited Media Enforcement (BLOCK)...")
    render_scene_scan_block(writer)

    print("Rendering Scene 5: Cryptographic Audit Verification...")
    render_scene_audit_verify(writer)

    print("Rendering Scene 6: Project Summary & Defense Card...")
    render_scene_summary(writer)

    writer.release()
    file_size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"\n[SUCCESS] Generated SafeGate Demo Video: {OUTPUT_FILE.resolve()}")
    print(f"Resolution: 1920x1080 (1080p Full HD) | FPS: 30 | Duration: 28 seconds | Size: {file_size_mb:.2f} MB")


if __name__ == "__main__":
    generate_full_demo()
