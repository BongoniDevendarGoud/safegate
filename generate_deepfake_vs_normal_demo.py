"""
SafeGate — Normal vs. Deepfake Screening Demonstration Video Generator
======================================================================
Produces a cinematic 1080p (1920x1080 @ 30 FPS) split-screen demonstration video
showing the complete terminal journey and real-time AI forensic inspection for:
  1. Authentic / Normal Video (`sample_clean.mp4`) -> Verdict: ALLOW (Published)
  2. Synthetic Deepfake Video (`sample_malicious_deepfake.mp4`) -> Verdict: REVIEW (Quarantined)
  3. Cryptographic Audit Log Verification (`python cli.py audit`)
"""

from pathlib import Path
import cv2
import numpy as np

OUTPUT_FILE = Path(__file__).resolve().parent / "safegate_normal_vs_deepfake_demo.mp4"
CLEAN_VIDEO = Path(__file__).resolve().parent / "sample_clean.mp4"
DEEPFAKE_VIDEO = Path(__file__).resolve().parent / "sample_malicious_deepfake.mp4"

WIDTH = 1920
HEIGHT = 1080
FPS = 30

# Colors (BGR)
BG_DESKTOP = (28, 18, 14)
TERM_BG = (14, 11, 10)
TERM_TITLE_BAR = (38, 30, 28)
TERM_BORDER = (60, 50, 48)

PANEL_BG = (22, 17, 15)
PANEL_HEADER = (36, 28, 25)
PANEL_BORDER = (55, 45, 42)

TEXT_WHITE = (245, 245, 245)
TEXT_MUTED = (165, 165, 165)
TEXT_GREEN = (100, 240, 60)
TEXT_AMBER = (30, 185, 255)     # Warm Yellow/Amber
TEXT_RED = (60, 70, 245)
TEXT_CYAN = (240, 190, 60)
TEXT_PROMPT = (255, 205, 90)

# Geometry
TERM_X = 35
TERM_Y = 80
TERM_W = 1220
TERM_H = 955

HUD_X = 1275
HUD_Y = 80
HUD_W = 610
HUD_H = 955

PREVIEW_X = HUD_X + 25
PREVIEW_Y = HUD_Y + 70
PREVIEW_W = 560
PREVIEW_H = 340


def load_video_frames(path: Path):
    """Loads all frames from a video into memory for smooth HUD playback."""
    cap = cv2.VideoCapture(str(path))
    frames = []
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()
    return frames


def create_base_canvas(title_sub="7-LAYER OSI ARCHITECTURE"):
    canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    canvas[:] = BG_DESKTOP

    # Subtle wallpaper grid lines
    for y in range(0, HEIGHT, 90):
        cv2.line(canvas, (0, y), (WIDTH, y), (35, 24, 18), 1)

    # Top Brand Header Bar
    cv2.rectangle(canvas, (0, 0), (WIDTH, 60), (40, 28, 22), -1)
    cv2.line(canvas, (0, 60), (WIDTH, 60), (70, 50, 40), 2)
    cv2.putText(canvas, "SAFEGATE  |  7-LAYER OSI VIDEO SECURITY SCREENING GATEWAY", (40, 38), cv2.FONT_HERSHEY_DUPLEX, 0.72, TEXT_WHITE, 2, cv2.LINE_AA)
    cv2.putText(canvas, f"MODE: FAIL-CLOSED  *  {title_sub}", (1280, 38), cv2.FONT_HERSHEY_DUPLEX, 0.58, TEXT_CYAN, 1, cv2.LINE_AA)

    # Terminal Frame (Left)
    cv2.rectangle(canvas, (TERM_X, TERM_Y), (TERM_X + TERM_W, TERM_Y + TERM_H), TERM_BG, -1)
    cv2.rectangle(canvas, (TERM_X, TERM_Y), (TERM_X + TERM_W, TERM_Y + TERM_H), TERM_BORDER, 2)
    cv2.rectangle(canvas, (TERM_X, TERM_Y), (TERM_X + TERM_W, TERM_Y + 40), TERM_TITLE_BAR, -1)
    cv2.line(canvas, (TERM_X, TERM_Y + 40), (TERM_X + TERM_W, TERM_Y + 40), TERM_BORDER, 1)
    cv2.putText(canvas, "Command Prompt -- SafeGate CLI Appliance (cmd.exe)", (TERM_X + 20, TERM_Y + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, TEXT_WHITE, 1, cv2.LINE_AA)

    # Close/Min buttons
    bx = TERM_X + TERM_W - 25
    cv2.circle(canvas, (bx, TERM_Y + 20), 6, (60, 60, 220), -1)
    cv2.circle(canvas, (bx - 20, TERM_Y + 20), 6, (120, 120, 120), -1)
    cv2.circle(canvas, (bx - 40, TERM_Y + 20), 6, (120, 120, 120), -1)

    # Forensic HUD Frame (Right)
    cv2.rectangle(canvas, (HUD_X, HUD_Y), (HUD_X + HUD_W, HUD_Y + HUD_H), PANEL_BG, -1)
    cv2.rectangle(canvas, (HUD_X, HUD_Y), (HUD_X + HUD_W, HUD_Y + HUD_H), PANEL_BORDER, 2)
    cv2.rectangle(canvas, (HUD_X, HUD_Y), (HUD_X + HUD_W, HUD_Y + 45), PANEL_HEADER, -1)
    cv2.line(canvas, (HUD_X, HUD_Y + 45), (HUD_X + HUD_W, HUD_Y + 45), PANEL_BORDER, 1)
    cv2.putText(canvas, "MEDIA INSPECTOR & AI FORENSICS", (HUD_X + 20, HUD_Y + 30), cv2.FONT_HERSHEY_DUPLEX, 0.62, TEXT_CYAN, 1, cv2.LINE_AA)

    return canvas


def draw_terminal(canvas, lines, cursor_pos=None):
    y = TERM_Y + 70
    for item in lines:
        if len(item) == 2:
            text, color = item
            scale, thick = 0.52, 1
        elif len(item) == 3:
            text, color, scale = item
            thick = 1
        else:
            text, color, scale, thick = item
        cv2.putText(canvas, text, (TERM_X + 25, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)
        y += 26

    if cursor_pos:
        cx, cy = cursor_pos
        cv2.rectangle(canvas, (cx, cy - 16), (cx + 9, cy + 2), TEXT_WHITE, -1)


def draw_hud(canvas, frame_img, state: dict):
    """
    Renders the right-hand forensic inspector HUD.
    state keys:
      - title: str
      - badge_text: str
      - badge_color: tuple
      - deepfake_score: int (0-100)
      - nsfw_score: float
      - signals: list of (name, val_str, ok_bool)
      - verdict_status: str
      - verdict_color: tuple
      - destination: str
    """
    # 1. Video Preview Box
    cv2.rectangle(canvas, (PREVIEW_X, PREVIEW_Y), (PREVIEW_X + PREVIEW_W, PREVIEW_Y + PREVIEW_H), (10, 8, 8), -1)
    border_col = state.get("badge_color", PANEL_BORDER)
    cv2.rectangle(canvas, (PREVIEW_X, PREVIEW_Y), (PREVIEW_X + PREVIEW_W, PREVIEW_Y + PREVIEW_H), border_col, 2)

    if frame_img is not None:
        resized = cv2.resize(frame_img, (PREVIEW_W, PREVIEW_H))
        canvas[PREVIEW_Y:PREVIEW_Y + PREVIEW_H, PREVIEW_X:PREVIEW_X + PREVIEW_W] = resized
        # Overlay border
        cv2.rectangle(canvas, (PREVIEW_X, PREVIEW_Y), (PREVIEW_X + PREVIEW_W, PREVIEW_Y + PREVIEW_H), border_col, 3)

        # Video Banner Tag
        tag_bg = border_col
        cv2.rectangle(canvas, (PREVIEW_X + 10, PREVIEW_Y + 12), (PREVIEW_X + 320, PREVIEW_Y + 40), (10, 10, 10), -1)
        cv2.rectangle(canvas, (PREVIEW_X + 10, PREVIEW_Y + 12), (PREVIEW_X + 320, PREVIEW_Y + 40), tag_bg, 1)
        cv2.putText(canvas, state.get("badge_text", "VIDEO FEED"), (PREVIEW_X + 20, PREVIEW_Y + 32), cv2.FONT_HERSHEY_SIMPLEX, 0.48, state.get("badge_color", TEXT_WHITE), 1, cv2.LINE_AA)
    else:
        # Standby text
        cv2.putText(canvas, "STANDBY -- WAITING FOR STREAM", (PREVIEW_X + 80, PREVIEW_Y + 180), cv2.FONT_HERSHEY_SIMPLEX, 0.65, TEXT_MUTED, 1, cv2.LINE_AA)

    # 2. Diagnostic Telemetry Details
    cur_y = PREVIEW_Y + PREVIEW_H + 30
    cv2.putText(canvas, "REAL-TIME FORENSIC TELEMETRY", (HUD_X + 25, cur_y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, TEXT_MUTED, 1, cv2.LINE_AA)
    cur_y += 10
    cv2.line(canvas, (HUD_X + 25, cur_y), (HUD_X + HUD_W - 25, cur_y), PANEL_BORDER, 1)
    cur_y += 30

    # Deepfake Gauge Bar
    df_score = state.get("deepfake_score", None)
    if df_score is not None:
        cv2.putText(canvas, "Deepfake Risk Score:", (HUD_X + 25, cur_y), cv2.FONT_HERSHEY_SIMPLEX, 0.52, TEXT_WHITE, 1, cv2.LINE_AA)
        score_col = TEXT_GREEN if df_score < 60 else (TEXT_RED if df_score >= 70 else TEXT_AMBER)
        cv2.putText(canvas, f"{df_score} / 100", (HUD_X + HUD_W - 120, cur_y), cv2.FONT_HERSHEY_DUPLEX, 0.6, score_col, 2, cv2.LINE_AA)
        cur_y += 15

        # Bar Background
        bar_x = HUD_X + 25
        bar_w = HUD_W - 50
        cv2.rectangle(canvas, (bar_x, cur_y), (bar_x + bar_w, cur_y + 16), (40, 32, 28), -1)
        # Threshold 60 marker
        thresh_x = int(bar_x + bar_w * 0.60)
        cv2.line(canvas, (thresh_x, cur_y - 4), (thresh_x, cur_y + 20), TEXT_AMBER, 2)
        cv2.putText(canvas, "Threshold: 60", (thresh_x - 45, cur_y + 32), cv2.FONT_HERSHEY_SIMPLEX, 0.38, TEXT_AMBER, 1, cv2.LINE_AA)

        # Fill Gauge
        fill_w = int(bar_w * (df_score / 100.0))
        cv2.rectangle(canvas, (bar_x, cur_y), (bar_x + fill_w, cur_y + 16), score_col, -1)
        cur_y += 45

    # Signals breakdown
    signals = state.get("signals", [])
    if signals:
        cv2.putText(canvas, "Forensic Signal Vectors:", (HUD_X + 25, cur_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, TEXT_MUTED, 1, cv2.LINE_AA)
        cur_y += 25
        for sig_name, sig_val, is_clean in signals:
            col = TEXT_GREEN if is_clean else TEXT_RED
            status_symbol = "[OK]" if is_clean else "[FAIL]"
            cv2.putText(canvas, f"{sig_name}:", (HUD_X + 30, cur_y), cv2.FONT_HERSHEY_SIMPLEX, 0.44, TEXT_WHITE, 1, cv2.LINE_AA)
            cv2.putText(canvas, f"{sig_val}  {status_symbol}", (HUD_X + HUD_W - 200, cur_y), cv2.FONT_HERSHEY_SIMPLEX, 0.44, col, 1, cv2.LINE_AA)
            cur_y += 24
        cur_y += 15

    # Final Verdict Card
    v_status = state.get("verdict_status", None)
    if v_status:
        v_col = state.get("verdict_color", TEXT_GREEN)
        cv2.rectangle(canvas, (HUD_X + 25, cur_y), (HUD_X + HUD_W - 25, cur_y + 90), (12, 10, 10), -1)
        cv2.rectangle(canvas, (HUD_X + 25, cur_y), (HUD_X + HUD_W - 25, cur_y + 90), v_col, 2)
        cv2.putText(canvas, f"GATE DECISION: {v_status}", (HUD_X + 45, cur_y + 36), cv2.FONT_HERSHEY_DUPLEX, 0.65, v_col, 2, cv2.LINE_AA)
        dest = state.get("destination", "Storage")
        cv2.putText(canvas, f"Storage Target: {dest}", (HUD_X + 45, cur_y + 68), cv2.FONT_HERSHEY_SIMPLEX, 0.48, TEXT_WHITE, 1, cv2.LINE_AA)


def generate_demo():
    print(f"Generating SafeGate Normal vs. Deepfake demo video...")
    clean_frames = load_video_frames(CLEAN_VIDEO)
    deepfake_frames = load_video_frames(DEEPFAKE_VIDEO)
    print(f"Loaded {len(clean_frames)} clean frames, {len(deepfake_frames)} deepfake frames.")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(OUTPUT_FILE), fourcc, FPS, (WIDTH, HEIGHT))

    if not writer.isOpened():
        raise RuntimeError("OpenCV VideoWriter failed to open.")

    # -------------------------------------------------------------------------
    # PART 1: Terminal Startup & SafeGate Tool Banner (0 - 4s, 120 frames)
    # -------------------------------------------------------------------------
    print("Writing Part 1: Terminal startup & tool initialization...")
    p1_cmd1 = "cd C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate"
    p1_cmd2 = "python cli.py"

    initial_lines = [
        ("Microsoft Windows [Version 10.0.22631.4317]", TEXT_MUTED),
        ("(c) Microsoft Corporation. All rights reserved.", TEXT_MUTED),
        ("", TEXT_MUTED),
    ]

    hud_idle = {
        "badge_text": "INPUT STANDBY",
        "badge_color": (80, 80, 80),
        "deepfake_score": None,
        "signals": [],
        "verdict_status": None,
    }

    # Type cd command (30 frames)
    for i in range(len(p1_cmd1) + 1):
        canvas = create_base_canvas()
        typed = p1_cmd1[:i]
        lines = initial_lines + [(f"C:\\Users\\user> {typed}", TEXT_WHITE)]
        cx = TERM_X + 25 + int(len(f"C:\\Users\\user> {typed}") * 9.5)
        cy = TERM_Y + 70 + (3 * 26)
        draw_terminal(canvas, lines, cursor_pos=(cx, cy))
        draw_hud(canvas, None, hud_idle)
        writer.write(canvas)

    # Press Enter and type python cli.py (35 frames)
    step1_lines = initial_lines + [
        (f"C:\\Users\\user> {p1_cmd1}", TEXT_MUTED),
        ("", TEXT_MUTED),
    ]
    for i in range(len(p1_cmd2) + 1):
        canvas = create_base_canvas()
        typed = p1_cmd2[:i]
        lines = step1_lines + [(f"C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> {typed}", TEXT_WHITE)]
        cx = TERM_X + 25 + int(len(f"C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> {typed}") * 9.5)
        cy = TERM_Y + 70 + (2 * 26)
        draw_terminal(canvas, lines, cursor_pos=(cx, cy))
        draw_hud(canvas, None, hud_idle)
        writer.write(canvas)

    # Show Banner (55 frames)
    banner_lines = [
        ("======================================================================", TEXT_CYAN, 0.54, 2),
        ("  SafeGate -- 7-Layer OSI Video Screening Gateway & CLI Appliance", TEXT_CYAN, 0.58, 2),
        ("======================================================================", TEXT_CYAN, 0.54, 2),
        ("Architecture: OSI Model Layers 1-7 | Mode: Fail-Closed & Tamper-Resistant", TEXT_MUTED),
        ("", TEXT_MUTED),
        ("COMMANDS:", TEXT_AMBER, 0.54, 2),
        ("  safegate scan <file>     Screen video through complete 7-Layer OSI stack", TEXT_WHITE),
        ("  safegate serve           Launch headless OSI network screening daemon", TEXT_WHITE),
        ("  safegate audit           Verify cryptographic SHA-256 audit chain integrity", TEXT_WHITE),
        ("  safegate stats           Display screening metrics and telemetry in terminal", TEXT_WHITE),
        ("", TEXT_MUTED),
    ]

    for _ in range(55):
        canvas = create_base_canvas()
        draw_terminal(canvas, step1_lines + [(f"C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> {p1_cmd2}", TEXT_WHITE)] + banner_lines + [
            ("C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate>", TEXT_WHITE)
        ])
        draw_hud(canvas, None, hud_idle)
        writer.write(canvas)

    # -------------------------------------------------------------------------
    # PART 2: Screening Normal / Authentic Video (`sample_clean.mp4`) (4 - 15s)
    # -------------------------------------------------------------------------
    print("Writing Part 2: Normal / authentic video screening...")
    cmd_clean = "python cli.py scan sample_clean.mp4"

    clean_base_history = [
        ("======================================================================", TEXT_CYAN, 0.54, 2),
        ("  SafeGate -- 7-Layer OSI Video Screening Gateway & CLI Appliance", TEXT_CYAN, 0.58, 2),
        ("======================================================================", TEXT_CYAN, 0.54, 2),
        ("Architecture: OSI Model Layers 1-7 | Mode: Fail-Closed & Tamper-Resistant", TEXT_MUTED),
        ("", TEXT_MUTED),
    ]

    # Type scan command (30 frames)
    for i in range(len(cmd_clean) + 1):
        canvas = create_base_canvas(title_sub="TEST 1: AUTHENTIC / NORMAL MEDIA")
        typed = cmd_clean[:i]
        lines = clean_base_history + [
            (f"C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> {typed}", TEXT_WHITE)
        ]
        cx = TERM_X + 25 + int(len(f"C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> {typed}") * 9.5)
        cy = TERM_Y + 70 + (5 * 26)
        draw_terminal(canvas, lines, cursor_pos=(cx, cy))
        draw_hud(canvas, None, hud_idle)
        writer.write(canvas)

    # Scan Header
    clean_scan_header = [
        (f"C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> {cmd_clean}", TEXT_WHITE),
        ("", TEXT_MUTED),
        ("Initiating OSI Protocol Stack Analysis on: sample_clean.mp4", TEXT_AMBER, 0.56, 2),
        ("Size: 55,215 bytes | Client IP: 127.0.0.1", TEXT_MUTED),
        ("", TEXT_MUTED),
        (f"{'LAYER':<12} {'SUBSYSTEM':<34} {'STATUS':<10} {'LATENCY':<10} {'DETAILS'}", TEXT_MUTED, 0.52, 2),
        ("-" * 88, TEXT_MUTED),
    ]

    clean_layers = [
        ("Layer 5", "Session (Authentication)", "PASS", "0.0ms", "Session authenticated for role 'client'.", TEXT_GREEN),
        ("Layer 3", "Network (Traffic Policing)", "PASS", "0.0ms", "IP 127.0.0.1 conforms to policy (1/10).", TEXT_GREEN),
        ("Layer 1", "Physical (Bitstream Ingestion)", "PASS", "0.5ms", "Stream buffered safely (55215 bytes).", TEXT_GREEN),
        ("Layer 6", "Presentation (Syntax Validation)", "PASS", "1.4ms", "MIME format confirmed: video/mp4 (.mp4)", TEXT_GREEN),
        ("Layer 4", "Transport (Integrity Checksum)", "PASS", "7.5ms", "SHA-256 clean: e7e95635df71ad41...", TEXT_GREEN),
        ("Layer 2", "Data Link (Temporal Framing)", "PASS", "34.5ms", "Extracted 3 synchronized frames.", TEXT_GREEN),
        ("Layer 6", "Presentation (pHash Dedup)", "PASS", "436.3ms", "Computed 3 frame pHashes. Blocklist clean.", TEXT_GREEN),
        ("Layer 7", "Application (Cognitive Policy)", "ALLOW", "60.1ms", "NSFW: 0.02, Deepfake: 10/100 -> ALLOW", TEXT_GREEN),
    ]

    hud_clean_active = {
        "badge_text": "AUTHENTIC CAMERA SENSOR VIDEO",
        "badge_color": TEXT_GREEN,
        "deepfake_score": 10,
        "nsfw_score": 0.02,
        "signals": [
            ("Sharpness Consistency", "CoV: 0.12", True),
            ("Temporal Color Flow", "Hist Corr: 0.98", True),
            ("Compression Quality", "MSE: 3.2", True),
            ("Camera Metadata", "Natural EXIF", True),
        ],
        "verdict_status": "ALLOW (PUBLISHED)",
        "verdict_color": TEXT_GREEN,
        "destination": "/published/a04b6ba01d6f.mp4",
    }

    # Step through layers (120 frames)
    clean_f_idx = 0
    for step_idx in range(1, len(clean_layers) + 1):
        visible_lines = []
        for l_num, sub, status, lat, det, col in clean_layers[:step_idx]:
            line_str = f"{l_num:<12} {sub:<34} {status:<10} {lat:<10} {det}"
            visible_lines.append((line_str, col, 0.50, 1))

        # Show current frame from clean video
        for _ in range(15):
            canvas = create_base_canvas(title_sub="TEST 1: AUTHENTIC / NORMAL MEDIA")
            draw_terminal(canvas, clean_base_history + clean_scan_header + visible_lines)
            frame_img = clean_frames[clean_f_idx % len(clean_frames)] if clean_frames else None
            clean_f_idx += 1
            draw_hud(canvas, frame_img, hud_clean_active)
            writer.write(canvas)

    # Verdict ALLOW Output (90 frames)
    clean_verdict_lines = [
        ("-" * 88, TEXT_MUTED),
        ("", TEXT_MUTED),
        (">>> FINAL VERDICT: ALLOW (Published) <<<", TEXT_GREEN, 0.72, 2),
        ("Upload ID:       a04b6ba01d6f4ea695a9a72c36973bfa", TEXT_WHITE),
        ("SHA-256:         e7e95635df71ad4129c203c854d4376c2b6fe7d122c12c23e88cde2ae4ab3cfb", TEXT_MUTED),
        ("NSFW Peak:       2.0% (Clean)", TEXT_WHITE),
        ("Deepfake Risk:   10/100 (Safe, Authentic Media)", TEXT_GREEN, 0.54, 2),
        ("Pipeline Time:   0.545 seconds", TEXT_CYAN, 0.54, 2),
        ("Explanation:     Clean: Media cleared all screening stages without triggering thresholds.", TEXT_WHITE),
        ("", TEXT_MUTED),
    ]

    for _ in range(90):
        canvas = create_base_canvas(title_sub="TEST 1 RESULT: ALLOWED & PUBLISHED")
        draw_terminal(canvas, clean_base_history + clean_scan_header + visible_lines + clean_verdict_lines)
        frame_img = clean_frames[clean_f_idx % len(clean_frames)] if clean_frames else None
        clean_f_idx += 1
        draw_hud(canvas, frame_img, hud_clean_active)
        writer.write(canvas)

    # -------------------------------------------------------------------------
    # PART 3: Screening Deepfake Video (`sample_malicious_deepfake.mp4`) (15 - 28s)
    # -------------------------------------------------------------------------
    print("Writing Part 3: Deepfake / synthetic video screening & quarantine...")
    cmd_deepfake = "python cli.py scan sample_malicious_deepfake.mp4"

    df_base_history = [
        ("======================================================================", TEXT_CYAN, 0.54, 2),
        ("  SafeGate -- 7-Layer OSI Video Screening Gateway & CLI Appliance", TEXT_CYAN, 0.58, 2),
        ("======================================================================", TEXT_CYAN, 0.54, 2),
        ("Architecture: OSI Model Layers 1-7 | Mode: Fail-Closed & Tamper-Resistant", TEXT_MUTED),
        ("", TEXT_MUTED),
    ]

    # Type scan command (30 frames)
    for i in range(len(cmd_deepfake) + 1):
        canvas = create_base_canvas(title_sub="TEST 2: SYNTHETIC / DEEPFAKE MEDIA")
        typed = cmd_deepfake[:i]
        lines = df_base_history + [
            (f"C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> {typed}", TEXT_WHITE)
        ]
        cx = TERM_X + 25 + int(len(f"C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> {typed}") * 9.5)
        cy = TERM_Y + 70 + (5 * 26)
        draw_terminal(canvas, lines, cursor_pos=(cx, cy))
        draw_hud(canvas, None, hud_idle)
        writer.write(canvas)

    df_scan_header = [
        (f"C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> {cmd_deepfake}", TEXT_WHITE),
        ("", TEXT_MUTED),
        ("Initiating OSI Protocol Stack Analysis on: sample_malicious_deepfake.mp4", TEXT_AMBER, 0.56, 2),
        ("Size: 1,187,899 bytes | Client IP: 127.0.0.1", TEXT_MUTED),
        ("", TEXT_MUTED),
        (f"{'LAYER':<12} {'SUBSYSTEM':<34} {'STATUS':<10} {'LATENCY':<10} {'DETAILS'}", TEXT_MUTED, 0.52, 2),
        ("-" * 88, TEXT_MUTED),
    ]

    df_layers = [
        ("Layer 5", "Session (Authentication)", "PASS", "0.0ms", "Session authenticated for role 'client'.", TEXT_GREEN),
        ("Layer 3", "Network (Traffic Policing)", "PASS", "0.0ms", "IP 127.0.0.1 conforms to policy (1/10).", TEXT_GREEN),
        ("Layer 1", "Physical (Bitstream Ingestion)", "PASS", "3.5ms", "Stream buffered safely (1187899 bytes).", TEXT_GREEN),
        ("Layer 6", "Presentation (Syntax Validation)", "PASS", "1.7ms", "MIME format confirmed: video/mp4 (.mp4)", TEXT_GREEN),
        ("Layer 4", "Transport (Integrity Checksum)", "PASS", "11.4ms", "SHA-256 clean: 4c962394ea21c44b...", TEXT_GREEN),
        ("Layer 2", "Data Link (Temporal Framing)", "PASS", "42.9ms", "Extracted 3 synchronized frames.", TEXT_GREEN),
        ("Layer 6", "Presentation (pHash Dedup)", "PASS", "471.6ms", "Computed 3 frame pHashes. Blocklist clean.", TEXT_GREEN),
        ("Layer 7", "Application (Cognitive Policy)", "REVIEW", "74.7ms", "NSFW: 0.02, Deepfake: 75/100 -> REVIEW", TEXT_AMBER),
    ]

    hud_df_active = {
        "badge_text": "! DEEPFAKE SYNTHETIC MANIPULATION !",
        "badge_color": TEXT_RED,
        "deepfake_score": 75,
        "nsfw_score": 0.02,
        "signals": [
            ("Sharpness Instability", "CoV: 0.71", False),
            ("Temporal Discontinuity", "Hist Corr: -0.05", False),
            ("Compression Artifacts", "MSE: 53.8", False),
            ("Missing Metadata", "No Camera Tags", False),
        ],
        "verdict_status": "REVIEW (QUARANTINED)",
        "verdict_color": TEXT_AMBER,
        "destination": "/quarantine/2177a3760d9b.mp4",
    }

    # Step through layers (120 frames)
    df_f_idx = 0
    for step_idx in range(1, len(df_layers) + 1):
        visible_lines = []
        for l_num, sub, status, lat, det, col in df_layers[:step_idx]:
            line_str = f"{l_num:<12} {sub:<34} {status:<10} {lat:<10} {det}"
            visible_lines.append((line_str, col, 0.50, 1))

        # Show current frame from deepfake video
        for _ in range(15):
            canvas = create_base_canvas(title_sub="TEST 2: SYNTHETIC / DEEPFAKE MEDIA")
            draw_terminal(canvas, df_base_history + df_scan_header + visible_lines)
            frame_img = deepfake_frames[df_f_idx % len(deepfake_frames)] if deepfake_frames else None
            df_f_idx += 1
            draw_hud(canvas, frame_img, hud_df_active)
            writer.write(canvas)

    # Verdict REVIEW Output with Deepfake Details (110 frames)
    df_verdict_lines = [
        ("-" * 88, TEXT_MUTED),
        ("", TEXT_MUTED),
        (">>> FINAL VERDICT: REVIEW (Quarantined) <<<", TEXT_AMBER, 0.72, 2),
        ("Upload ID:       2177a3760d9b4b58a6dcd138d1847279", TEXT_WHITE),
        ("SHA-256:         4c962394ea21c44b5862ad2a09ade7c5cf94865f71beb4b06f6581512010d1e0", TEXT_MUTED),
        ("NSFW Peak:       2.0%", TEXT_WHITE),
        ("Deepfake Risk:   75/100 (Exceeds Review Threshold: 60)", TEXT_RED, 0.54, 2),
        ("Pipeline Time:   0.610 seconds", TEXT_CYAN, 0.54, 2),
        ("Advisory Signals: CoV: 0.71 (Flicker) | Color Corr: -0.05 | MSE: 53.8 | Missing EXIF", TEXT_AMBER, 0.48, 1),
        ("Quarantine Path: Media moved to secure isolation vault for human review.", TEXT_WHITE),
        ("", TEXT_MUTED),
    ]

    for _ in range(110):
        canvas = create_base_canvas(title_sub="TEST 2 RESULT: QUARANTINED (DEEPFAKE RISK 75/100)")
        draw_terminal(canvas, df_base_history + df_scan_header + visible_lines + df_verdict_lines)
        frame_img = deepfake_frames[df_f_idx % len(deepfake_frames)] if deepfake_frames else None
        df_f_idx += 1
        draw_hud(canvas, frame_img, hud_df_active)
        writer.write(canvas)

    # -------------------------------------------------------------------------
    # PART 4: Cryptographic Audit Chain Verification (28 - 36s, 240 frames)
    # -------------------------------------------------------------------------
    print("Writing Part 4: Cryptographic audit verification...")
    cmd_audit = "python cli.py audit"

    audit_pre_lines = [
        ("C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> " + cmd_audit, TEXT_WHITE),
        ("", TEXT_MUTED),
        ("Verifying Cryptographic SHA-256 Audit Hash Chain...", TEXT_CYAN, 0.56, 2),
        ("-----------------------------------------------------------------", TEXT_MUTED),
        ("[+] AUDIT INTEGRITY: VALID (Cryptographic Chain Intact)", TEXT_GREEN, 0.68, 2),
        ("Total Sequential Records: 23 tamper-evident entries verified", TEXT_WHITE),
        ("Broken at Row ID:         None (Zero tampering detected)", TEXT_WHITE),
        ("Verification Summary:     Audit chain verified: all 23 entries intact.", TEXT_MUTED),
        ("-----------------------------------------------------------------", TEXT_MUTED),
        ("", TEXT_MUTED),
        ("C:\\Users\\user\\.gemini\\antigravity\\scratch\\safegate> _", TEXT_PROMPT, 0.55, 2),
    ]

    hud_audit = {
        "badge_text": "TAMPER-PROOF AUDIT TRAIL",
        "badge_color": TEXT_GREEN,
        "deepfake_score": None,
        "signals": [
            ("Ledger Type", "HMAC SHA-256 Hash Chain", True),
            ("Verification Status", "ALL 23 RECORDS INTACT", True),
            ("Chain Compromise", "0 Broken Links", True),
            ("Enforcement Rule", "Fail-Closed Gateway Active", True),
        ],
        "verdict_status": "AUDIT VERIFIED [OK]",
        "verdict_color": TEXT_GREEN,
        "destination": "Local Immutable SQLite Audit Store",
    }

    for _ in range(120):
        canvas = create_base_canvas(title_sub="CRYPTOGRAPHIC AUDIT CHAIN VERIFICATION")
        draw_terminal(canvas, audit_pre_lines)
        draw_hud(canvas, None, hud_audit)
        writer.write(canvas)

    writer.release()
    size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"\n[SUCCESS] Demo video generated successfully: {OUTPUT_FILE.resolve()}")
    print(f"File: {OUTPUT_FILE.name} | Size: {size_mb:.2f} MB | Resolution: 1920x1080 Full HD @ 30 FPS")


if __name__ == "__main__":
    generate_demo()
