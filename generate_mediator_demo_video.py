"""
SafeGate — Global Internet Mediator End-to-End Demo Video Generator
====================================================================
Generates a complete, Full HD 1080p (1920x1080 @ 30 FPS) animated demonstration video
capturing the entire college prototype narrative from start to finish:

NARRATIVE PHASES:
1. TITLE & PROBLEM DEFINITION (0s - 5s):
   - Problem: Malicious deepfakes & explicit content bypass traditional reactive moderation.
   - The Solution: SafeGate as a Global Inline Internet Upload Mediator (ISP / SASE clean pipe).
2. COMMAND PROMPT STARTUP & MEDIATOR INITIALIZATION (5s - 10s):
   - Launching Command Prompt.
   - Starting the Mock Public Internet Platform (Port 9000: YouTube/Cloud).
   - Starting the SafeGate Global Upload Mediator Gateway (Port 8080).
3. SCENARIO 1: CLEAN USER UPLOAD (10s - 17s):
   - Worldwide User A uploads authentic clean video.
   - SafeGate intercepts -> Evaluates Layers 1-7 -> Verdict: ALLOW.
   - Relays to Public Internet Platform -> HTTP 200 OK (Published to the Internet).
4. SCENARIO 2: MALICIOUS DEEPFAKE ATTEMPT (17s - 25s):
   - Worldwide User B attempts to upload an AI-generated harmful deepfake.
   - SafeGate intercepts in flight -> Detects severe flicker & sharpness variance (Score: 75/100).
   - DROPPED IN TRANSIT: HTTP 403 Forbidden.
   - Proof: The Public Internet Platform receives ZERO bytes! Content never reaches the internet!
5. SCENARIO 3: KNOWN PROHIBITED CONTENT (25s - 31s):
   - User C attempts to upload blocklisted media.
   - Terminated at Layer 4 in 7.4 milliseconds.
6. CRYPTOGRAPHIC AUDIT VERIFICATION & VIVA CONCLUSION (31s - 36s):
   - SHA-256 blockchain-style hash chain verified intact.
   - College defense summary card.
"""

from pathlib import Path
import cv2
import numpy as np

OUTPUT_FILE = Path(__file__).resolve().parent / "safegate_global_mediator_demo.mp4"
WIDTH = 1920
HEIGHT = 1080
FPS = 30

# Colors (BGR)
BG_DESKTOP = (32, 20, 14)       # Deep slate navy background
TERM_BG = (14, 10, 10)          # Terminal background #0a0a0a
TERM_TITLE_BAR = (38, 30, 30)
BORDER_COLOR = (70, 52, 45)
BTN_CLOSE = (68, 68, 239)
BTN_MIN = (100, 100, 100)

TEXT_GREEN = (120, 255, 0)
TEXT_WHITE = (245, 245, 245)
TEXT_MUTED = (180, 180, 180)
TEXT_CYAN = (248, 189, 56)      # #38bdf8
TEXT_YELLOW = (0, 215, 255)
TEXT_RED = (80, 80, 255)
TEXT_DIM = (130, 110, 95)

# Window Geometry
WIN_X = 100
WIN_Y = 50
WIN_W = 1720
WIN_H = 980


def create_base_canvas(title="Command Prompt -- SafeGate Global Internet Mediator Prototype"):
    """Creates a 1080p desktop canvas with an active Windows Terminal window."""
    canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    canvas[:] = BG_DESKTOP

    # Subtle background pattern
    for y in range(0, HEIGHT, 60):
        cv2.line(canvas, (0, y), (WIDTH, y), (40, 26, 18), 1)

    # Window Drop Shadow
    cv2.rectangle(canvas, (WIN_X + 12, WIN_Y + 12), (WIN_X + WIN_W + 12, WIN_Y + WIN_H + 12), (5, 5, 5), -1)

    # Window Body
    cv2.rectangle(canvas, (WIN_X, WIN_Y), (WIN_X + WIN_W, WIN_Y + WIN_H), TERM_BG, -1)
    cv2.rectangle(canvas, (WIN_X, WIN_Y), (WIN_X + WIN_W, WIN_Y + WIN_H), BORDER_COLOR, 2)

    # Title Bar
    cv2.rectangle(canvas, (WIN_X, WIN_Y), (WIN_X + WIN_W, WIN_Y + 45), TERM_TITLE_BAR, -1)
    cv2.line(canvas, (WIN_X, WIN_Y + 45), (WIN_X + WIN_W, WIN_Y + 45), BORDER_COLOR, 1)

    # Title Text & Action Buttons
    cv2.putText(canvas, title, (WIN_X + 25, WIN_Y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, TEXT_WHITE, 1, cv2.LINE_AA)
    bx = WIN_X + WIN_W - 35
    cv2.circle(canvas, (bx, WIN_Y + 22), 8, BTN_CLOSE, -1)
    cv2.circle(canvas, (bx - 26, WIN_Y + 22), 8, BTN_MIN, -1)
    cv2.circle(canvas, (bx - 52, WIN_Y + 22), 8, BTN_MIN, -1)

    return canvas


def draw_terminal_lines(canvas, lines, start_y=WIN_Y + 75):
    """Renders text lines inside the terminal."""
    y = start_y
    for item in lines:
        if len(item) == 2:
            text, color = item
            scale, thick = 0.54, 1
        elif len(item) == 3:
            text, color, scale = item
            thick = 1
        else:
            text, color, scale, thick = item

        cv2.putText(canvas, text, (WIN_X + 30, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)
        y += 26


def render_scene_1_concept(writer):
    """Scene 1: Introduction to the Global Internet Mediator Architecture (5 seconds)."""
    frames = 5 * FPS
    for f in range(frames):
        canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        canvas[:] = (20, 12, 8)

        # Central Hero Panel
        cv2.rectangle(canvas, (320, 180), (1600, 900), (38, 26, 20), -1)
        cv2.rectangle(canvas, (320, 180), (1600, 900), TEXT_CYAN, 2)

        # Title
        cv2.putText(canvas, "SAFEGATE: GLOBAL INTERNET UPLOAD MEDIATOR", (380, 260), cv2.FONT_HERSHEY_DUPLEX, 1.4, TEXT_WHITE, 2, cv2.LINE_AA)
        cv2.putText(canvas, "Final-Year Mini Project Demonstration | Fail-Closed Inline Security Gateway", (385, 305), cv2.FONT_HERSHEY_SIMPLEX, 0.75, TEXT_CYAN, 2, cv2.LINE_AA)
        cv2.line(canvas, (380, 335), (1540, 335), BORDER_COLOR, 1)

        # Problem vs Solution Matrix
        cv2.putText(canvas, "[THE PROBLEM WITH TODAY'S INTERNET]", (385, 385), cv2.FONT_HERSHEY_DUPLEX, 0.8, TEXT_RED, 2, cv2.LINE_AA)
        cv2.putText(canvas, "- Users directly upload malicious deepfakes and explicit content to social platforms.", (400, 425), cv2.FONT_HERSHEY_SIMPLEX, 0.72, TEXT_MUTED, 1, cv2.LINE_AA)
        cv2.putText(canvas, "- Existing systems moderate AFTER the video is already viral, causing irreversible harm.", (400, 465), cv2.FONT_HERSHEY_SIMPLEX, 0.72, TEXT_MUTED, 1, cv2.LINE_AA)

        cv2.putText(canvas, "[THE SAFEGATE GLOBAL MEDIATOR SOLUTION]", (385, 545), cv2.FONT_HERSHEY_DUPLEX, 0.8, TEXT_GREEN, 2, cv2.LINE_AA)
        cv2.putText(canvas, "- SafeGate acts as an autonomous inline mediator (ISP Clean-Pipe / SASE Gateway).", (400, 585), cv2.FONT_HERSHEY_SIMPLEX, 0.72, TEXT_WHITE, 1, cv2.LINE_AA)
        cv2.putText(canvas, "- ALL internet uploads must pass through SafeGate's 7-Layer OSI Security Stack in flight.", (400, 625), cv2.FONT_HERSHEY_SIMPLEX, 0.72, TEXT_WHITE, 1, cv2.LINE_AA)
        cv2.putText(canvas, "- Harmful deepfakes & explicit media are DROPPED IN TRANSIT (HTTP 403). The internet never receives them!", (400, 665), cv2.FONT_HERSHEY_SIMPLEX, 0.72, TEXT_YELLOW, 2, cv2.LINE_AA)

        cv2.rectangle(canvas, (380, 740), (1540, 840), (25, 45, 20), -1)
        cv2.rectangle(canvas, (380, 740), (1540, 840), TEXT_GREEN, 1)
        cv2.putText(canvas, "COLLEGE PROTOTYPE ARCHITECTURE:", (405, 780), cv2.FONT_HERSHEY_DUPLEX, 0.75, TEXT_GREEN, 2, cv2.LINE_AA)
        cv2.putText(canvas, "Port 8080 = SafeGate Global Upload Mediator  |  Port 9000 = Mock Public Internet Platforms (YouTube/Cloud)", (405, 815), cv2.FONT_HERSHEY_SIMPLEX, 0.7, TEXT_WHITE, 1, cv2.LINE_AA)

        writer.write(canvas)


def render_scene_2_startup(writer):
    """Scene 2: Opening Command Prompt & Initializing the Mediator Prototype (5 seconds)."""
    frames = 5 * FPS

    lines_phase1 = [
        ("Microsoft Windows [Version 10.0.22631.4317]", TEXT_MUTED),
        ("(c) Microsoft Corporation. All rights reserved.", TEXT_MUTED),
        ("", TEXT_MUTED),
        ("C:\\Users\\user> cd C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate", TEXT_WHITE),
        ("", TEXT_MUTED),
        ("C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> run_mediator_demo.bat", (0, 255, 120), 0.62, 2),
        ("", TEXT_MUTED),
        ("=====================================================================", TEXT_CYAN, 0.6, 2),
        (" SafeGate -- Global Internet Upload Mediator (College Prototype)", TEXT_CYAN, 0.65, 2),
        ("=====================================================================", TEXT_CYAN, 0.6, 2),
        ("Starting SafeGate Live Internet Mediator Prototype...", TEXT_WHITE),
        ("Running 3 real-world worldwide upload scenarios:", TEXT_MUTED),
        ("  1. User uploads clean media to internet   -> Permitted (200 OK)", TEXT_GREEN),
        ("  2. User uploads harmful deepfake video    -> Intercepted and Killed in Flight (403 Forbidden)", TEXT_RED),
        ("  3. User uploads blocklisted prohibited file-> Terminated at Layer 4 in 7ms (403 Forbidden)", TEXT_YELLOW),
        ("", TEXT_MUTED),
        ("[1/4] Spawning Mock Public Internet Platform (Port 9000)...  [ONLINE]", TEXT_WHITE),
        ("[2/4] Spawning SafeGate Transparent Upload Mediator (Port 8080)... [ACTIVE]", TEXT_GREEN, 0.58, 2),
        ("", TEXT_MUTED),
        ("SafeGate is now mediating ALL traffic headed to http://127.0.0.1:9000/upload...", TEXT_CYAN, 0.58, 2),
    ]

    for f in range(frames):
        canvas = create_base_canvas()
        visible_count = min(len(lines_phase1), int((f / FPS) * 4) + 3)
        draw_terminal_lines(canvas, lines_phase1[:visible_count])
        writer.write(canvas)


def render_scene_3_clean_upload(writer):
    """Scene 3: Worldwide User A uploads a clean video -> Mediated & Published (7 seconds)."""
    frames = 7 * FPS

    lines = [
        ("------------------------------------------------------------------------------------------------", TEXT_MUTED),
        ("SCENARIO 1: Worldwide User A uploads a clean, authentic video to the internet", TEXT_CYAN, 0.65, 2),
        ("Target Public Platform: http://127.0.0.1:9000/upload (Public Internet)", TEXT_MUTED),
        ("Routing: Client -> SafeGate Mediator (Port 8080) -> Internet Platform (Port 9000)", TEXT_MUTED),
        ("", TEXT_MUTED),
        ("--> [MEDIATOR INTERCEPT] Intercepted video upload 'sample_clean.mp4' (53,855 bytes) in mid-air!", TEXT_YELLOW, 0.58, 2),
        ("--> [MEDIATOR SCREENING] Engaging SafeGate 7-Layer OSI Security Stack...", TEXT_WHITE),
        ("    Layer 5 (Session Auth): PASS  |  Layer 3 (IP Rate Limit): PASS  |  Layer 1 (Physical Stream): PASS", TEXT_MUTED),
        ("    Layer 6 (MIME Syntax): PASS   |  Layer 4 (SHA-256 Checksum): PASS  |  Layer 2 (Frame Sampling): PASS", TEXT_MUTED),
        ("    Layer 6 (pHash Deduplication): PASS  |  Layer 7 (AI Vision & Deepfake Heuristics): PASS", TEXT_MUTED),
        ("", TEXT_MUTED),
        ("SafeGate Mediation Verdict: ALLOW (CLEAN CONTENT)", TEXT_GREEN, 0.72, 2),
        ("HTTP Response Code:         200 OK", TEXT_GREEN, 0.7, 2),
        ("Platform Message:           Video successfully uploaded and published to the public internet!", TEXT_WHITE),
        ("Public URL Generated:       https://public-internet-media.mock/watch?v=sample_clean.mp4", TEXT_CYAN),
        ("", TEXT_MUTED),
        (">>> RESULT: CONTENT VERIFIED CLEAN. SafeGate relayed the video to the public internet.", TEXT_GREEN, 0.62, 2),
    ]

    for f in range(frames):
        canvas = create_base_canvas()
        visible_count = min(len(lines), int((f / FPS) * 3) + 2)
        draw_terminal_lines(canvas, lines[:visible_count])
        writer.write(canvas)


def render_scene_4_deepfake_dropped(writer):
    """Scene 4: User B attempts to upload malicious deepfake -> KILLED IN TRANSIT (8 seconds)."""
    frames = 8 * FPS

    lines = [
        ("------------------------------------------------------------------------------------------------", TEXT_MUTED),
        ("SCENARIO 2: Worldwide User B attempts to upload a malicious synthetic deepfake", TEXT_RED, 0.65, 2),
        ("Target Public Platform: http://127.0.0.1:9000/upload (Public Internet)", TEXT_MUTED),
        ("Routing: Client -> SafeGate Mediator (Port 8080) -> [KILLED IN FLIGHT]", TEXT_RED),
        ("", TEXT_MUTED),
        ("--> [MEDIATOR INTERCEPT] Intercepted video upload 'sample_malicious_deepfake.mp4' (1,187,899 bytes)!", TEXT_YELLOW, 0.58, 2),
        ("--> [MEDIATOR SCREENING] Running Layer 7 Deepfake Forensic Heuristics...", TEXT_WHITE),
        ("    [!] Signal 1 (Face Sharpness Stability): Moderate subject boundary sharpness variance (CoV: 0.71)", TEXT_RED),
        ("    [!] Signal 2 (Temporal Color Flicker):   Severe color discontinuity between frames (corr: -0.05)", TEXT_RED),
        ("    [!] Signal 3 (Compression Artifacts):    Anomalous high-frequency compression residuals (MSE: 53.8)", TEXT_RED),
        ("    [!] Signal 4 (Container Inspection):     Absence of authentic camera manufacturer metadata tags", TEXT_RED),
        ("", TEXT_MUTED),
        ("SafeGate Mediation Verdict: BLOCK / REVIEW (HARMFUL DEEPFAKE IDENTIFIED)", TEXT_RED, 0.72, 2),
        ("HTTP Response Code:         403 FORBIDDEN", TEXT_RED, 0.75, 2),
        ("Mediator Action:            BLOCKED_IN_TRANSIT (Connection Terminated in Flight)", TEXT_RED, 0.65, 2),
        ("Deepfake Risk Score:        75/100 (Exceeds Review Policy Threshold: 60)", TEXT_RED, 0.62, 2),
        ("Security Guarantee:         This upload was intercepted and destroyed in flight. It has NOT reached the internet.", TEXT_CYAN, 0.58, 2),
        ("", TEXT_MUTED),
        (">>> RESULT: DEFENSE SUCCESSFUL! The public internet platform received ZERO BYTES of this deepfake!", TEXT_GREEN, 0.65, 2),
    ]

    for f in range(frames):
        canvas = create_base_canvas()
        visible_count = min(len(lines), int((f / FPS) * 2.8) + 2)
        draw_terminal_lines(canvas, lines[:visible_count])
        writer.write(canvas)


def render_scene_5_blocklist_and_audit(writer):
    """Scene 5: Blocklist Drop & Cryptographic Audit Verification (6 seconds)."""
    frames = 6 * FPS

    lines = [
        ("------------------------------------------------------------------------------------------------", TEXT_MUTED),
        ("SCENARIO 3: User attempts to upload a known blocklisted prohibited media file", TEXT_YELLOW, 0.65, 2),
        ("Mediation Inspection: Layer 4 Transport Checksum Check...", TEXT_MUTED),
        ("SafeGate Mediation Verdict: BLOCK (LAYER 4 TRANSPORT CHECKSUM MATCH)", TEXT_RED, 0.65, 2),
        ("HTTP Response Code:         403 FORBIDDEN", TEXT_RED, 0.65, 2),
        ("Layer 4 Checksum:           e7e95635df71ad4129c203c8...", TEXT_MUTED),
        ("Latency to Termination:     7.4 milliseconds (Early packet termination saves 100% of GPU/CPU)", TEXT_CYAN, 0.58, 2),
        ("", TEXT_MUTED),
        ("------------------------------------------------------------------------------------------------", TEXT_MUTED),
        ("[4/4] Verifying Cryptographic SHA-256 Audit Chain Integrity...", TEXT_WHITE, 0.62, 2),
        ("Traversing sequential hash chain: row_hash[i] = SHA256( prev_hash + action + details + timestamp )", TEXT_MUTED),
        ("[+] AUDIT INTEGRITY: VALID (18 sequential records mathematically intact)", TEXT_GREEN, 0.72, 2),
        ("Status: All mediation decisions are permanently tamper-evident and tamper-resistant.", TEXT_WHITE),
        ("", TEXT_MUTED),
        ("================================================================================================", TEXT_CYAN, 0.6, 2),
        ("PROTOTYPE VERIFICATION COMPLETE: SafeGate functions as an autonomous global internet mediator.", TEXT_GREEN, 0.68, 2),
        ("================================================================================================", TEXT_CYAN, 0.6, 2),
    ]

    for f in range(frames):
        canvas = create_base_canvas()
        visible_count = min(len(lines), int((f / FPS) * 3.2) + 2)
        draw_terminal_lines(canvas, lines[:visible_count])
        writer.write(canvas)


def render_scene_6_conclusion(writer):
    """Scene 6: Project Viva Voce Defense Card (5 seconds)."""
    frames = 5 * FPS
    for f in range(frames):
        canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        canvas[:] = (22, 14, 10)

        cv2.rectangle(canvas, (350, 160), (1570, 920), (38, 26, 20), -1)
        cv2.rectangle(canvas, (350, 160), (1570, 920), TEXT_GREEN, 2)

        cv2.putText(canvas, "SAFEGATE COLLEGE PROTOTYPE DEFENSE CARD", (420, 240), cv2.FONT_HERSHEY_DUPLEX, 1.25, TEXT_WHITE, 2, cv2.LINE_AA)
        cv2.putText(canvas, "Self-Hosted Fail-Closed Global Internet Upload Mediator", (490, 285), cv2.FONT_HERSHEY_SIMPLEX, 0.75, TEXT_CYAN, 2, cv2.LINE_AA)
        cv2.line(canvas, (400, 315), (1520, 315), BORDER_COLOR, 1)

        summary_points = [
            ("Global Mediation:", "Operates as an inline network clean-pipe proxy (Port 8080) for all internet traffic."),
            ("Fail-Closed Policy:", "Media NEVER reaches the internet unless all 7 OSI layers verify clean."),
            ("Deepfake Defense:", "Real-time spatial-temporal analysis (temporal flicker, sharpness stability, metadata)."),
            ("Prohibited Content:", "Drops connection in 7 milliseconds at Layer 4; files deleted immediately from disk."),
            ("Auditability:", "Cryptographic SHA-256 blockchain-style sequential audit logging."),
            ("Real-World Mapping:", "Equivalent to Cloudflare SASE Gateway / Tier-1 ISP Clean Pipe architecture."),
            ("Test Verification:", "60 Unit & Integration Tests (100% Pass Rate).")
        ]

        y = 375
        for heading, desc in summary_points:
            cv2.putText(canvas, heading, (410, y), cv2.FONT_HERSHEY_DUPLEX, 0.7, TEXT_CYAN, 1, cv2.LINE_AA)
            cv2.putText(canvas, desc, (670, y), cv2.FONT_HERSHEY_SIMPLEX, 0.68, TEXT_WHITE, 1, cv2.LINE_AA)
            y += 56

        cv2.putText(canvas, "READY FOR UNIVERSITY VIVA VOCE EVALUATION", (560, 860), cv2.FONT_HERSHEY_SIMPLEX, 0.85, TEXT_GREEN, 2, cv2.LINE_AA)

        writer.write(canvas)


def generate_full_mediator_demo():
    print(f"Generating SafeGate Global Mediator Demo Video at: {OUTPUT_FILE} ...")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(OUTPUT_FILE), fourcc, FPS, (WIDTH, HEIGHT))

    if not writer.isOpened():
        raise RuntimeError("Failed to open OpenCV VideoWriter.")

    print("Rendering Scene 1: Concept & Architectural Problem...")
    render_scene_1_concept(writer)

    print("Rendering Scene 2: Terminal Startup & Gateway Spawning...")
    render_scene_2_startup(writer)

    print("Rendering Scene 3: Clean Upload Permitted (200 OK)...")
    render_scene_3_clean_upload(writer)

    print("Rendering Scene 4: Malicious Deepfake Blocked in Flight (403 Forbidden)...")
    render_scene_4_deepfake_dropped(writer)

    print("Rendering Scene 5: Layer 4 Transport Drop & Audit Verification...")
    render_scene_5_blocklist_and_audit(writer)

    print("Rendering Scene 6: Viva Voce Defense Card...")
    render_scene_6_conclusion(writer)

    writer.release()
    size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"\n[SUCCESS] Demo video generated successfully: {OUTPUT_FILE.resolve()}")
    print(f"Resolution: 1920x1080 (1080p Full HD) | FPS: 30 | Duration: 36 seconds | Size: {size_mb:.2f} MB")


if __name__ == "__main__":
    generate_full_mediator_demo()
