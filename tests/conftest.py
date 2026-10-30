"""
SafeGate — Test Fixtures & Configuration (conftest.py)
========================================================
Configures pytest fixtures, isolated temporary directories, and in-memory test databases.

DEFENSIVE TESTING RULE:
We programmatically generate synthetic MP4 test videos using OpenCV.
No explicit, copyrighted, or sensitive material is ever stored or tested.
"""

import os
import shutil
import tempfile
from pathlib import Path
import pytest
import numpy as np
import cv2

# Set isolated test environment variables BEFORE importing app settings
_temp_test_dir = tempfile.mkdtemp(prefix="safegate_pytest_")
os.environ["ADMIN_API_KEY"] = "test-admin-key-12345"
os.environ["CLIENT_API_KEY"] = "test-client-key-67890"
os.environ["USE_GEMINI"] = "false"
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_temp_test_dir) / 'test_safegate.db'}"
os.environ["QUARANTINE_DIR"] = str(Path(_temp_test_dir) / "quarantine")
os.environ["REVIEW_DIR"] = str(Path(_temp_test_dir) / "review")
os.environ["PUBLISHED_DIR"] = str(Path(_temp_test_dir) / "published")
os.environ["BLOCK_THRESHOLD"] = "0.85"
os.environ["REVIEW_THRESHOLD"] = "0.45"
os.environ["MAX_UPLOAD_SIZE_MB"] = "10"  # Reduced limit for rapid test execution

from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine, SessionLocal


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Ensures isolated temporary directories exist and tears them down after tests.
    """
    for d in ["quarantine", "review", "published"]:
        (Path(_temp_test_dir) / d).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    yield
    shutil.rmtree(_temp_test_dir, ignore_errors=True)


@pytest.fixture
def client():
    """
    Provides a synchronous TestClient communicating directly with the FastAPI application.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session():
    """
    Provides a clean database session per test.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def generate_synthetic_video():
    """
    Generates a small, valid, safe MP4 video programmatically using OpenCV.
    Draws simple color patterns so tests are fully reproducible and ethical.
    """
    created_files = []

    def _create(duration_sec: int = 2, fps: int = 10, width: int = 160, height: int = 120) -> tuple:
        fd, tmp_path_str = tempfile.mkstemp(suffix=".mp4", dir=_temp_test_dir)
        os.close(fd)
        tmp_path = Path(tmp_path_str)
        created_files.append(tmp_path)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(tmp_path), fourcc, fps, (width, height))

        total_frames = duration_sec * fps
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]  # BGR colors

        for i in range(total_frames):
            color = colors[i % len(colors)]
            frame = np.full((height, width, 3), color, dtype=np.uint8)
            writer.write(frame)

        writer.release()
        video_bytes = tmp_path.read_bytes()
        return (tmp_path, video_bytes)

    yield _create

    for f in created_files:
        if f.exists():
            f.unlink()
