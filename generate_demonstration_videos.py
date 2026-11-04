"""
SafeGate 2.0 — Demonstration Scenario Video Generator
=====================================================
Generates deterministic test videos for all 6 end-to-end scenarios:
- Scenario 1: Legitimate Authentic Video (clears all checks -> ALLOW -> Published)
- Scenario 2: Deepfake Manipulated Video (synthetic noise/flicker -> QUARANTINE -> GREEN frames)
- Scenario 3: Single AI-Modified Frame (Frame #25 is modified -> QUARANTINE -> Frame #25 GREEN, others RED)
- Scenario 4: Uncertain Classification (Low quality / ambiguous blur -> QUARANTINE -> YELLOW frames)
- Scenario 5: Corrupted Media Stream (Truncated / malformed bitstream -> BLOCK -> Rejected)
- Scenario 6: AI Model Failure (Triggers fail-closed policy -> QUARANTINE)
"""

import sys
from pathlib import Path
import cv2
import numpy as np

# Storage directory for sample scenarios
DEMO_DIR = Path(__file__).resolve().parent / "samples"
DEMO_DIR.mkdir(parents=True, exist_ok=True)


def create_scenario1_legitimate(out_path: Path):
    """Scenario 1: Authentic, pristine video capture."""
    width, height = 320, 240
    fps = 15
    num_frames = 45
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))

    for i in range(num_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Natural continuous lighting gradient
        frame[:, :, 0] = np.linspace(25, 65, width, dtype=np.uint8)
        frame[:, :, 1] = np.linspace(45, 95, height, dtype=np.uint8).reshape(-1, 1)
        frame[:, :, 2] = 85

        # Natural sensor noise (CMOS simulation)
        noise = np.random.normal(0, 2.0, (height, width, 3)).astype(np.int16)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Smooth moving subject (natural kinematics)
        cx = int(width / 2 + (width / 5) * np.sin(i / 5.0))
        cy = int(height / 2 + (height / 6) * np.cos(i / 5.0))
        cv2.circle(frame, (cx, cy), 28, (60, 220, 140), -1)
        cv2.circle(frame, (cx, cy), 18, (255, 255, 255), -1)

        cv2.putText(
            frame,
            f"Scenario 1: Authentic [Frame {i+1}]",
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        writer.write(frame)

    writer.release()
    print(f"[+] Generated Scenario 1: {out_path.name}")


def create_scenario2_deepfake(out_path: Path):
    """Scenario 2: Video with synthetic generative artifacts and temporal flicker."""
    width, height = 320, 240
    fps = 15
    num_frames = 45
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))

    for i in range(num_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Alternating artificial flicker
        if i % 2 == 0:
            frame[:, :, 0] = 220
            frame[:, :, 1] = 20
            frame[:, :, 2] = 190
            # High-frequency synthetic noise (JPEG residual MSE > 40.0)
            noise = np.random.randint(0, 140, (height, width, 3), dtype=np.uint8)
            frame = cv2.add(frame, noise)
        else:
            frame[:, :, 0] = 15
            frame[:, :, 1] = 210
            frame[:, :, 2] = 25
            # Heavy artificial blur
            frame = cv2.GaussianBlur(frame, (31, 31), 0)

        cv2.putText(
            frame,
            f"Scenario 2: Deepfake [Frame {i+1}]",
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )
        writer.write(frame)

    writer.release()
    print(f"[+] Generated Scenario 2: {out_path.name}")


def create_scenario3_single_modified_frame(out_path: Path):
    """
    Scenario 3: Crucial Scenario!
    A 45-frame authentic video where exactly ONE frame (Frame #25) is synthetically modified.
    Frames 1-24 & 26-45 are legitimate (RED). Frame 25 is modified (GREEN).
    SafeGate must isolate Frame #25 and quarantine the entire video.
    """
    width, height = 320, 240
    fps = 15
    num_frames = 45
    tampered_index = 25  # Frame #25 is modified
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))

    for i in range(num_frames):
        frame_num = i + 1
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        if frame_num == tampered_index:
            # THIS IS THE SINGLE SYNTHETICALLY TAMPERED FRAME
            frame[:, :, 0] = 230
            frame[:, :, 1] = 40
            frame[:, :, 2] = 210
            # Inject extreme high-frequency synthetic compression noise
            noise = np.random.randint(0, 180, (height, width, 3), dtype=np.uint8)
            frame = cv2.add(frame, noise)
            for k in range(8):
                cv2.rectangle(frame, (60 + k*12, 40 + k*12), (180 + k*6, 160 + k*6), (255, 255, 255), 2)
            cv2.putText(
                frame,
                f"** AI-MODIFIED FRAME #{frame_num} **",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 0, 0),
                1,
                cv2.LINE_AA,
            )
        else:
            # AUTHENTIC LEGITIMATE FRAME
            frame[:, :, 0] = np.linspace(30, 70, width, dtype=np.uint8)
            frame[:, :, 1] = np.linspace(40, 100, height, dtype=np.uint8).reshape(-1, 1)
            frame[:, :, 2] = 90
            cx = int(width / 2 + (width / 5) * np.sin(i / 5.0))
            cy = int(height / 2 + (height / 6) * np.cos(i / 5.0))
            cv2.circle(frame, (cx, cy), 25, (80, 210, 130), -1)
            cv2.putText(
                frame,
                f"Authentic Frame #{frame_num}",
                (12, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

        writer.write(frame)

    writer.release()
    print(f"[+] Generated Scenario 3: {out_path.name} (Tampered Frame #{tampered_index})")


def create_scenario4_uncertain(out_path: Path):
    """Scenario 4: Ambiguous / low-contrast video triggering UNCERTAIN classification (YELLOW)."""
    width, height = 320, 240
    fps = 15
    num_frames = 30
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))

    for i in range(num_frames):
        # Uniform flat grey background (extremely low Laplacian variance < 3.0)
        frame = np.full((height, width, 3), 110, dtype=np.uint8)
        # Slight blur
        frame = cv2.GaussianBlur(frame, (15, 15), 0)

        cv2.putText(
            frame,
            f"Scenario 4: Low Clarity #{i+1}",
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (130, 130, 130),
            1,
            cv2.LINE_AA,
        )
        writer.write(frame)

    writer.release()
    print(f"[+] Generated Scenario 4: {out_path.name}")


def create_scenario5_corrupted(out_path: Path):
    """Scenario 5: Corrupted, non-decodable video container."""
    with open(out_path, "wb") as f:
        # Invalid truncated header
        f.write(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42\xff\xff\x00MALFORMED_BITSTREAM_CORRUPTION")
        f.write(b"\x00" * 1024)
    print(f"[+] Generated Scenario 5: {out_path.name}")


def ensure_demonstration_videos() -> dict:
    """Ensures all 6 demonstration videos exist on disk and returns paths."""
    p1 = DEMO_DIR / "scenario1_legitimate.mp4"
    p2 = DEMO_DIR / "scenario2_deepfake.mp4"
    p3 = DEMO_DIR / "scenario3_single_modified.mp4"
    p4 = DEMO_DIR / "scenario4_uncertain.mp4"
    p5 = DEMO_DIR / "scenario5_corrupted.mp4"

    if not p1.exists():
        create_scenario1_legitimate(p1)
    if not p2.exists():
        create_scenario2_deepfake(p2)
    if not p3.exists():
        create_scenario3_single_modified_frame(p3)
    if not p4.exists():
        create_scenario4_uncertain(p4)
    if not p5.exists():
        create_scenario5_corrupted(p5)

    return {
        "legitimate": p1,
        "deepfake": p2,
        "single_modified": p3,
        "uncertain": p4,
        "corrupted": p5,
    }


if __name__ == "__main__":
    ensure_demonstration_videos()
