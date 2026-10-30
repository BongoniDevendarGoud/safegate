"""
SafeGate — Realistic Interactive Terminal Demo Video Generator
==============================================================
Generates a realistic, cinematic 1080p (1920x1080 @ 30 FPS) demonstration video
recording the exact end-to-end user terminal journey:

JOURNEY PHASES:
1. Windows Desktop & Launching Command Prompt (cmd.exe window opens).
2. Navigating to directory: `cd C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate`.
3. Loading the SafeGate Tool: running `python cli.py` to show banner, commands, and OSI architecture.
4. User selects a video: `sample_clean.mp4` and runs `python cli.py scan sample_clean.mp4`.
5. Real-time character typing animation + live 7-Layer OSI Protocol Stack execution.
6. SafeGate inspects the video:
   - Layer 5 Session Auth -> PASS
   - Layer 3 Network Rate -> PASS
   - Layer 1 Physical Bitstream -> PASS
   - Layer 6 Presentation Syntax -> PASS
   - Layer 4 Transport SHA-256 Checksum -> PASS
   - Layer 2 Data Link Video Framing -> PASS
   - Layer 6 Perceptual pHash -> PASS
   - Layer 7 Application AI Vision & Deepfake Scorer -> PASS
7. The gateway renders the verdict: >>> FINAL VERDICT: ALLOW (Published) <<<.
8. Testing a prohibited/violating file:
   - User types: `python cli.py scan prohibited_video.mp4`
   - Layer 4 detects blocklisted transport hash in 7ms!
   - Pipeline immediately terminates with: >>> FINAL VERDICT: BLOCK (Deleted & Blocklisted) <<<.
9. User checks cryptographic audit chain: `python cli.py audit` -> Chain Intact.
"""

from pathlib import Path
import cv2
import numpy as np

OUTPUT_FILE = Path(__file__).resolve().parent / "safegate_terminal_walkthrough.mp4"
WIDTH = 1920
HEIGHT = 1080
FPS = 30

# Windows Terminal Theme Colors (BGR)
BG_DESKTOP = (38, 22, 14)       # Deep dark desktop background
TERM_BG = (16, 12, 12)          # Black terminal background #0c0c0c
TERM_TITLE_BAR = (38, 32, 32)   # Dark gray window header
TERM_BORDER = (65, 55, 55)
BTN_CLOSE = (68, 68, 239)       # Red window close button
BTN_MIN = (100, 100, 100)

# Syntax & Output Colors (BGR)
TEXT_GREEN = (120, 255, 0)      # Terminal bright green
TEXT_WHITE = (245, 245, 245)
TEXT_MUTED = (180, 180, 180)
TEXT_CYAN = (248, 189, 56)      # #38bdf8
TEXT_YELLOW = (0, 215, 255)     # #ffd700
TEXT_RED = (80, 80, 255)        # #ff5050
TEXT_PROMPT = (255, 200, 80)    # PowerShell / CMD prompt accent

# Window Geometry (Centered terminal window)
WIN_X = 140
WIN_Y = 60
WIN_W = 1640
WIN_H = 960


def create_base_canvas():
    """Renders the desktop with a Windows Terminal / CMD window frame."""
    canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    canvas[:] = BG_DESKTOP

    # Subtle desktop wallpaper gradient / grid line
    for y in range(0, HEIGHT, 80):
        cv2.line(canvas, (0, y), (WIDTH, y), (45, 28, 18), 1)

    # Terminal Window Shadow
    cv2.rectangle(canvas, (WIN_X + 15, WIN_Y + 15), (WIN_X + WIN_W + 15, WIN_Y + WIN_H + 15), (5, 5, 5), -1)

    # Terminal Body
    cv2.rectangle(canvas, (WIN_X, WIN_Y), (WIN_X + WIN_W, WIN_Y + WIN_H), TERM_BG, -1)
    cv2.rectangle(canvas, (WIN_X, WIN_Y), (WIN_X + WIN_W, WIN_Y + WIN_H), TERM_BORDER, 2)

    # Window Title Bar
    cv2.rectangle(canvas, (WIN_X, WIN_Y), (WIN_X + WIN_W, WIN_Y + 45), TERM_TITLE_BAR, -1)
    cv2.line(canvas, (WIN_X, WIN_Y + 45), (WIN_X + WIN_W, WIN_Y + 45), TERM_BORDER, 1)

    # Window Title
    cv2.putText(canvas, "Command Prompt -- SafeGate 7-Layer OSI Security Gateway", (WIN_X + 25, WIN_Y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, TEXT_WHITE, 1, cv2.LINE_AA)

    # Window Buttons (Minimize, Maximize, Close)
    bx = WIN_X + WIN_W - 35
    cv2.circle(canvas, (bx, WIN_Y + 22), 8, BTN_CLOSE, -1)
    cv2.circle(canvas, (bx - 26, WIN_Y + 22), 8, BTN_MIN, -1)
    cv2.circle(canvas, (bx - 52, WIN_Y + 22), 8, BTN_MIN, -1)

    return canvas


def draw_terminal_lines(canvas, lines, start_y=WIN_Y + 80, cursor_pos=None):
    """
    Renders terminal text lines with monospace aesthetic.
    lines is a list of tuples: (text, color, font_scale, thickness)
    """
    y = start_y
    for item in lines:
        if len(item) == 2:
            text, color = item
            scale, thick = 0.58, 1
        elif len(item) == 3:
            text, color, scale = item
            thick = 1
        else:
            text, color, scale, thick = item

        cv2.putText(canvas, text, (WIN_X + 30, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)
        y += 28

    if cursor_pos:
        cx, cy = cursor_pos
        cv2.rectangle(canvas, (cx, cy - 18), (cx + 10, cy + 3), TEXT_WHITE, -1)


def generate_walkthrough_video():
    print(f"Recording interactive Command Prompt walkthrough at: {OUTPUT_FILE} ...")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(OUTPUT_FILE), fourcc, FPS, (WIDTH, HEIGHT))

    if not writer.isOpened():
        raise RuntimeError("Failed to initialize OpenCV VideoWriter.")

    # =========================================================================
    # PHASE 1: Terminal Opens with Initial Windows Prompt (2.5 seconds)
    # =========================================================================
    print("Recording Phase 1: Terminal startup & directory navigation...")
    initial_text = "Microsoft Windows [Version 10.0.22631.4317]\n(c) Microsoft Corporation. All rights reserved."
    base_lines = [
        ("Microsoft Windows [Version 10.0.22631.4317]", TEXT_MUTED),
        ("(c) Microsoft Corporation. All rights reserved.", TEXT_MUTED),
        ("", TEXT_MUTED),
    ]

    # Typing: cd C:\Users\user\.gemini\antigravity\scratch\safegate
    cmd1 = "cd C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate"
    for i in range(len(cmd1) + 1):
        canvas = create_base_canvas()
        typed = cmd1[:i]
        curr_lines = base_lines + [
            (f"C:\\Users\\user> {typed}", TEXT_WHITE)
        ]
        cursor_x = WIN_X + 30 + int(len(f"C:\\Users\\user> {typed}") * 10.8)
        cursor_y = WIN_Y + 80 + (3 * 28)
        draw_terminal_lines(canvas, curr_lines, cursor_pos=(cursor_x, cursor_y))
        writer.write(canvas)
        # Small delay per character
        if i < len(cmd1):
            writer.write(canvas)

    # Press Enter
    for _ in range(25):
        canvas = create_base_canvas()
        curr_lines = base_lines + [
            (f"C:\\Users\\user> {cmd1}", TEXT_WHITE),
            ("", TEXT_MUTED),
            ("C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate>", TEXT_WHITE)
        ]
        cursor_x = WIN_X + 30 + int(len("C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate>") * 10.8)
        cursor_y = WIN_Y + 80 + (5 * 28)
        draw_terminal_lines(canvas, curr_lines, cursor_pos=(cursor_x, cursor_y))
        writer.write(canvas)

    # =========================================================================
    # PHASE 2: Launching SafeGate Tool (python cli.py) (3.5 seconds)
    # =========================================================================
    print("Recording Phase 2: Loading SafeGate Tool...")
    cmd2 = "python cli.py"
    history = [
        ("C:\\Users\\user> " + cmd1, TEXT_MUTED),
        ("", TEXT_MUTED),
    ]

    for i in range(len(cmd2) + 1):
        canvas = create_base_canvas()
        typed = cmd2[:i]
        curr_lines = history + [
            (f"C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> {typed}", TEXT_WHITE)
        ]
        cursor_x = WIN_X + 30 + int(len(f"C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> {typed}") * 10.8)
        cursor_y = WIN_Y + 80 + (2 * 28)
        draw_terminal_lines(canvas, curr_lines, cursor_pos=(cursor_x, cursor_y))
        writer.write(canvas)

    # SafeGate Banner & Available Commands Load
    banner_lines = [
        ("======================================================================", TEXT_CYAN, 0.6, 2),
        ("  SafeGate -- 7-Layer OSI Video Screening Gateway & CLI Appliance", TEXT_CYAN, 0.65, 2),
        ("======================================================================", TEXT_CYAN, 0.6, 2),
        ("Architecture: OSI Model Layers 1-7 | Mode: Fail-Closed & Tamper-Resistant", TEXT_MUTED),
        ("", TEXT_MUTED),
        ("COMMANDS:", TEXT_YELLOW, 0.6, 2),
        ("  safegate scan <file>     Screen a video through the complete 7-Layer OSI stack", TEXT_WHITE),
        ("  safegate serve           Launch the headless OSI network screening server", TEXT_WHITE),
        ("  safegate audit           Verify cryptographic SHA-256 audit chain integrity", TEXT_WHITE),
        ("  safegate blocklist       Query or manage exact & perceptual blocklists", TEXT_WHITE),
        ("  safegate stats           Display screening metrics and telemetry in terminal", TEXT_WHITE),
        ("", TEXT_MUTED),
    ]

    for _ in range(70):
        canvas = create_base_canvas()
        draw_terminal_lines(canvas, history + [(f"C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> {cmd2}", TEXT_WHITE)] + banner_lines + [
            ("C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate>", TEXT_WHITE)
        ])
        writer.write(canvas)

    # =========================================================================
    # PHASE 3: Adding & Scanning Video (python cli.py scan sample_clean.mp4) (7 seconds)
    # =========================================================================
    print("Recording Phase 3: Ingesting video & live 7-Layer OSI inspection...")
    cmd3 = "python cli.py scan sample_clean.mp4"

    scan_history = [
        ("======================================================================", TEXT_CYAN, 0.6, 2),
        ("  SafeGate -- 7-Layer OSI Video Screening Gateway & CLI Appliance", TEXT_CYAN, 0.65, 2),
        ("======================================================================", TEXT_CYAN, 0.6, 2),
        ("Architecture: OSI Model Layers 1-7 | Mode: Fail-Closed & Tamper-Resistant", TEXT_MUTED),
        ("", TEXT_MUTED),
    ]

    for i in range(len(cmd3) + 1):
        canvas = create_base_canvas()
        typed = cmd3[:i]
        curr_lines = scan_history + [
            (f"C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> {typed}", TEXT_WHITE)
        ]
        cursor_x = WIN_X + 30 + int(len(f"C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> {typed}") * 10.8)
        cursor_y = WIN_Y + 80 + (5 * 28)
        draw_terminal_lines(canvas, curr_lines, cursor_pos=(cursor_x, cursor_y))
        writer.write(canvas)

    # Header for Layer Execution
    init_scan_lines = [
        (f"C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> {cmd3}", TEXT_WHITE),
        ("", TEXT_MUTED),
        ("Initiating OSI Protocol Stack Analysis on: sample_clean.mp4", TEXT_YELLOW, 0.62, 2),
        ("Size: 53,855 bytes | Client IP: 127.0.0.1 | Format: MP4 Container", TEXT_MUTED),
        ("", TEXT_MUTED),
        (f"{'LAYER':<12} {'SUBSYSTEM':<34} {'STATUS':<10} {'LATENCY':<10} {'DETAILS'}", TEXT_MUTED, 0.58, 2),
        ("-" * 86, TEXT_MUTED),
    ]

    # Live sequential Layer arrivals
    layer_steps = [
        ("Layer 5", "Session (Authentication)", "PASS", "0.0ms", "Session authenticated for role 'client'.", TEXT_GREEN),
        ("Layer 3", "Network (Traffic Policing)", "PASS", "0.0ms", "IP 127.0.0.1 conforms to policy (1/10).", TEXT_GREEN),
        ("Layer 1", "Physical (Bitstream Ingestion)", "PASS", "0.2ms", "Stream buffered safely (53,855 bytes).", TEXT_GREEN),
        ("Layer 6", "Presentation (Syntax Validation)", "PASS", "3.4ms", "MIME format confirmed: video/mp4 (.mp4).", TEXT_GREEN),
        ("Layer 4", "Transport (Integrity Checksum)", "PASS", "8.7ms", "SHA-256 clean: d0be492050488172...", TEXT_GREEN),
        ("Layer 2", "Data Link (Temporal Framing)", "PASS", "66.2ms", "Extracted 3 synchronized frames.", TEXT_GREEN),
        ("Layer 6", "Presentation (pHash Deduplication)", "PASS", "719.5ms", "Computed 3 frame pHashes. Blocklist clean.", TEXT_GREEN),
        ("Layer 7", "Application (Cognitive Policy)", "ALLOW", "102.4ms", "NSFW: 0.02, Deepfake: 10/100 -> ALLOW", TEXT_GREEN),
    ]

    for step_idx in range(1, len(layer_steps) + 1):
        visible_layer_lines = []
        for l_num, sub, status, lat, det, col in layer_steps[:step_idx]:
            line_str = f"{l_num:<12} {sub:<34} {status:<10} {lat:<10} {det}"
            visible_layer_lines.append((line_str, col, 0.56, 1))

        # Hold on each layer for 8 frames to create realistic processing illusion
        for _ in range(8):
            canvas = create_base_canvas()
            draw_terminal_lines(canvas, scan_history + init_scan_lines + visible_layer_lines)
            writer.write(canvas)

    # Final Verdict ALLOW Badge
    verdict_lines = [
        ("-" * 86, TEXT_MUTED),
        ("", TEXT_MUTED),
        (">>> FINAL VERDICT: ALLOW (Published to storage) <<<", TEXT_GREEN, 0.78, 2),
        ("Upload ID:       14382f200dc844fbb0f31902c16ff846", TEXT_WHITE),
        ("SHA-256:         d0be4920504881722653251bb916fd116bdcb7244f67a1db22c112feef2a11b9", TEXT_MUTED),
        ("NSFW Peak Score: 2.0% (Clean)", TEXT_WHITE),
        ("Deepfake Risk:   10/100 (Authentic Sensor Capture)", TEXT_WHITE),
        ("Pipeline Time:   0.903 seconds", TEXT_CYAN, 0.6, 2),
        ("Explanation:     Clean: Media cleared all screening stages without triggering thresholds.", TEXT_WHITE),
        ("", TEXT_MUTED),
    ]

    for _ in range(90):  # Hold 3 seconds
        canvas = create_base_canvas()
        draw_terminal_lines(canvas, scan_history + init_scan_lines + visible_layer_lines + verdict_lines)
        writer.write(canvas)

    # =========================================================================
    # PHASE 4: Prohibited Media Detection & Instant BLOCK (6 seconds)
    # =========================================================================
    print("Recording Phase 4: Prohibited media detection & early BLOCK enforcement...")
    cmd4 = "python cli.py scan prohibited_video.mp4"

    block_pre_lines = [
        ("C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> " + cmd4, TEXT_WHITE),
        ("", TEXT_MUTED),
        ("Initiating OSI Protocol Stack Analysis on: prohibited_video.mp4", TEXT_YELLOW, 0.62, 2),
        ("Size: 4,821,902 bytes | Client IP: 127.0.0.1", TEXT_MUTED),
        ("", TEXT_MUTED),
        (f"{'LAYER':<12} {'SUBSYSTEM':<34} {'STATUS':<10} {'LATENCY':<10} {'DETAILS'}", TEXT_MUTED, 0.58, 2),
        ("-" * 86, TEXT_MUTED),
    ]

    block_steps = [
        ("Layer 5", "Session (Authentication)", "PASS", "0.0ms", "Session authenticated for role 'client'.", TEXT_GREEN),
        ("Layer 3", "Network (Traffic Policing)", "PASS", "0.0ms", "IP conforms to rate policy.", TEXT_GREEN),
        ("Layer 1", "Physical (Bitstream Ingestion)", "PASS", "0.1ms", "Stream buffered safely.", TEXT_GREEN),
        ("Layer 6", "Presentation (Syntax Validation)", "PASS", "2.0ms", "MIME format confirmed: video/mp4.", TEXT_GREEN),
        ("Layer 4", "Transport (Integrity Checksum)", "BLOCKED", "7.4ms", "[Layer 4 Violation] Checksum matched exact blocklist!", TEXT_RED),
    ]

    visible_block_lines = []
    for l_num, sub, status, lat, det, col in block_steps:
        line_str = f"{l_num:<12} {sub:<34} {status:<10} {lat:<10} {det}"
        visible_block_lines.append((line_str, col, 0.56, 1))

    block_verdict = [
        ("-" * 86, TEXT_MUTED),
        ("", TEXT_MUTED),
        (">>> FINAL VERDICT: BLOCK (Deleted & Blocklisted) <<<", TEXT_RED, 0.78, 2),
        ("Upload ID:       6cb4b990752b499d931b148e28893614", TEXT_WHITE),
        ("Pipeline Time:   0.010 seconds (Early Termination: Saved 100% of GPU/CPU inference)", TEXT_CYAN, 0.6, 2),
        ("Action Taken:    Quarantined file permanently unlinked from disk (Zero Storage Policy).", TEXT_WHITE),
        ("Explanation:     [Layer 4 Transport Violation] Checksum matched in exact blocklist.", TEXT_RED),
        ("", TEXT_MUTED),
    ]

    for _ in range(120):  # Hold 4 seconds
        canvas = create_base_canvas()
        draw_terminal_lines(canvas, block_pre_lines + visible_block_lines + block_verdict)
        writer.write(canvas)

    # =========================================================================
    # PHASE 5: Cryptographic Audit Verification (python cli.py audit) (4 seconds)
    # =========================================================================
    print("Recording Phase 5: Cryptographic Audit Verification...")
    cmd5 = "python cli.py audit"

    audit_lines = [
        ("C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> " + cmd5, TEXT_WHITE),
        ("", TEXT_MUTED),
        ("Verifying Cryptographic SHA-256 Audit Hash Chain...", TEXT_CYAN, 0.62, 2),
        ("-----------------------------------------------------------------", TEXT_MUTED),
        ("[+] AUDIT INTEGRITY: VALID (Cryptographic Chain Intact)", TEXT_GREEN, 0.72, 2),
        ("Total Sequential Records: 7 entries verified", TEXT_WHITE),
        ("Broken at Row ID:         None (Zero tampering detected)", TEXT_WHITE),
        ("Verification Summary:     Audit chain verified: all 7 entries are cryptographically intact.", TEXT_MUTED),
        ("-----------------------------------------------------------------", TEXT_MUTED),
        ("", TEXT_MUTED),
        ("C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> _", TEXT_PROMPT, 0.6, 2),
    ]

    for _ in range(100):  # Hold 3.3 seconds
        canvas = create_base_canvas()
        draw_terminal_lines(canvas, audit_lines)
        writer.write(canvas)

    writer.release()
    size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"\n[SUCCESS] Walkthrough video generated: {OUTPUT_FILE.resolve()}")
    print(f"Resolution: 1920x1080 Full HD | FPS: 30 | Duration: ~23 seconds | Size: {size_mb:.2f} MB")


if __name__ == "__main__":
    generate_walkthrough_video()
