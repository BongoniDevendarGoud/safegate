"""
SafeGate — Test Samples Generator for Global Internet Mediation Demo
=====================================================================
Generates:
1. sample_clean.mp4: A smooth, authentic video representing clean user uploads.
2. sample_malicious_deepfake.mp4: A synthetic video with high temporal flicker
   and synthetic compression noise engineered to trigger SafeGate's deepfake heuristics.
"""

from pathlib import Path
import cv2
import numpy as np

OUTPUT_DIR = Path(__file__).resolve().parent


def create_clean_sample(output_path: Path):
    """Generates an authentic, smooth video (ALLOW)."""
    width, height = 320, 240
    fps = 15
    num_frames = 60
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    for i in range(num_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Smooth continuous gradient
        frame[:, :, 0] = np.linspace(20, 80, width, dtype=np.uint8)
        frame[:, :, 1] = np.linspace(40, 110, height, dtype=np.uint8).reshape(-1, 1)
        frame[:, :, 2] = 90

        # Moving smooth object
        cx = int(width / 2 + (width / 4) * np.sin(i / 6.0))
        cy = int(height / 2 + (height / 4) * np.cos(i / 6.0))
        cv2.circle(frame, (cx, cy), 25, (0, 220, 120), -1)

        cv2.putText(
            frame,
            f"Authentic Clean Video [Frame {i}]",
            (15, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        writer.write(frame)

    writer.release()
    print(f"[+] Created clean sample: {output_path.name} ({output_path.stat().st_size} bytes)")


def create_deepfake_flicker_sample(output_path: Path):
    """Generates a synthetic manipulated video with intense frame-to-frame sharpness jumps and color flicker."""
    width, height = 320, 240
    fps = 15
    num_frames = 60
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    for i in range(num_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Extreme alternating luminance/color flicker
        if i % 2 == 0:
            frame[:, :, 0] = 230
            frame[:, :, 1] = 20
            frame[:, :, 2] = 200
            # Extreme high-frequency artificial sharpness/noise
            noise = np.random.randint(0, 180, (height, width, 3), dtype=np.uint8)
            frame = cv2.add(frame, noise)
            # Draw jagged shapes in center ROI to maximize Laplacian variance
            for k in range(10):
                cv2.rectangle(frame, (80 + k*10, 60 + k*10), (160 + k*5, 140 + k*5), (255, 255, 255), 2)
        else:
            frame[:, :, 0] = 10
            frame[:, :, 1] = 220
            frame[:, :, 2] = 30
            # Extreme blur to produce low Laplacian variance
            frame = cv2.GaussianBlur(frame, (45, 45), 0)

        cv2.putText(
            frame,
            f"Synthetically Manipulated Frame {i}",
            (15, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )
        writer.write(frame)

    writer.release()
    print(f"[+] Created synthetic flicker sample: {output_path.name} ({output_path.stat().st_size} bytes)")


if __name__ == "__main__":
    create_clean_sample(OUTPUT_DIR / "sample_clean.mp4")
    create_deepfake_flicker_sample(OUTPUT_DIR / "sample_malicious_deepfake.mp4")
