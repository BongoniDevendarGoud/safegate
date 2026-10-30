"""
SafeGate — Generate Sample Test Video
=====================================
Generates a small, clean, compliant test video (sample_clean.mp4)
containing a simple animated geometric pattern with timestamp text.
Can be dragged and dropped into the SafeGate dashboard or uploaded via API.
"""

from pathlib import Path
import cv2
import numpy as np

def create_sample_video(output_path: Path, num_frames: int = 60, fps: int = 15):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 320, 240
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    for i in range(num_frames):
        # Create an attractive gradient frame with moving circle
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :, 0] = np.linspace(20, 60, width, dtype=np.uint8)
        frame[:, :, 1] = np.linspace(40, 100, height, dtype=np.uint8).reshape(-1, 1)
        frame[:, :, 2] = 80

        # Moving circle
        cx = int(width / 2 + (width / 4) * np.sin(i / 5.0))
        cy = int(height / 2 + (height / 4) * np.cos(i / 5.0))
        cv2.circle(frame, (cx, cy), 25, (0, 220, 120), -1)

        # Text banner
        cv2.putText(
            frame,
            f"SafeGate Clean Test Frame {i}",
            (15, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        writer.write(frame)

    writer.release()
    print(f"Generated sample test video at: {output_path.resolve()} ({output_path.stat().st_size} bytes)")

if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "sample_clean.mp4"
    create_sample_video(out)
