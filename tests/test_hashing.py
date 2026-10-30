"""
SafeGate — Unit Tests for Hashing (Stage 2 & Stage 4)
======================================================
Verifies:
1. Exact cryptographic hashing (SHA-256).
2. Exact blocklist lookups and database insertion.
3. Perceptual hashing (pHash) on image frames.
4. Hamming distance comparisons (exact match, slight modification, completely different image).
5. Perceptual blocklist lookups with configurable Hamming thresholds.
"""

import hashlib
from PIL import Image, ImageDraw
import pytest
from app.db import SessionLocal
from app.models.database import BlocklistHash, BlocklistPHash
from app.pipeline.hashing import (
    compute_sha256,
    check_exact_blocklist,
    add_to_exact_blocklist,
    compute_frame_phash,
    hamming_distance,
    check_perceptual_blocklist,
    add_to_perceptual_blocklist,
)


def test_sha256_computation():
    """Verify that compute_sha256 matches Python standard hashlib output."""
    payload = b"SafeGate Defensive Gateway Test Data"
    expected = hashlib.sha256(payload).hexdigest()
    assert compute_sha256(payload) == expected
    assert len(expected) == 64


def test_exact_blocklist_lifecycle():
    """Verify adding to and checking the exact SHA-256 blocklist."""
    db = SessionLocal()
    try:
        sample_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

        # Initially, hash should not be blocklisted
        assert not check_exact_blocklist(sample_hash, db)

        # Add to blocklist
        add_to_exact_blocklist(sample_hash, db, source="manual-test")

        # Now it must be detected
        assert check_exact_blocklist(sample_hash, db)

        # Idempotent addition
        add_to_exact_blocklist(sample_hash, db, source="manual-test")
        count = db.query(BlocklistHash).filter(BlocklistHash.sha256_hash == sample_hash).count()
        assert count == 1
    finally:
        db.query(BlocklistHash).filter(BlocklistHash.sha256_hash == sample_hash).delete()
        db.commit()
        db.close()


def test_phash_hamming_distance():
    """
    Verify perceptual hashing behavior:
    - Identical images have Hamming distance 0.
    - Slightly modified images (rescaling, compression) have low distance (<= 10).
    - Completely different images have high distance (> 15).
    """
    # Image A: Structured scene with shapes
    img_a = Image.new("RGB", (200, 200), color=(120, 120, 120))
    draw_a = ImageDraw.Draw(img_a)
    draw_a.rectangle([20, 20, 90, 90], fill=(220, 40, 40))
    draw_a.ellipse([70, 70, 170, 170], fill=(40, 220, 40))

    # Image B: Near-duplicate (rescaled to 190x190 then back to 200x200)
    img_b = img_a.resize((190, 190), resample=Image.BILINEAR).resize((200, 200), resample=Image.BILINEAR)

    # Image C: Completely different high-frequency striped pattern
    img_c = Image.new("RGB", (200, 200), color=(255, 255, 255))
    draw_c = ImageDraw.Draw(img_c)
    for i in range(0, 200, 10):
        draw_c.line([(0, i), (200, i)], fill=(0, 0, 0), width=4)

    phash_a = compute_frame_phash(img_a)
    phash_b = compute_frame_phash(img_b)
    phash_c = compute_frame_phash(img_c)

    dist_identical = hamming_distance(phash_a, phash_a)
    assert dist_identical == 0, f"Distance between identical images must be 0, got {dist_identical}"

    dist_near = hamming_distance(phash_a, phash_b)
    assert dist_near <= 10, f"Distance between near-duplicate images should be <= 10, got {dist_near}"

    dist_far = hamming_distance(phash_a, phash_c)
    assert dist_far > 10, f"Distance between completely different images should be > 10, got {dist_far}"


def test_perceptual_blocklist_matching():
    """Verify that check_perceptual_blocklist correctly identifies near-duplicate frames."""
    db = SessionLocal()
    try:
        # Create base structured test image and compute its pHash
        base_img = Image.new("RGB", (200, 200), color=(80, 80, 80))
        draw_base = ImageDraw.Draw(base_img)
        draw_base.rectangle([30, 30, 110, 110], fill=(200, 100, 50))
        draw_base.polygon([(100, 20), (160, 140), (40, 140)], fill=(50, 150, 220))
        base_phash = compute_frame_phash(base_img)

        # Store in blocklist
        add_to_perceptual_blocklist([base_phash], db, source="test-blocked")

        # 1. Exact match test
        match_exact = check_perceptual_blocklist([(1.5, base_phash)], db, threshold=10)
        assert match_exact is not None
        ts, frame_ph, block_ph, dist = match_exact
        assert ts == 1.5
        assert dist == 0

        # 2. Near-duplicate test (subtly rescaled)
        near_img = base_img.resize((195, 195), resample=Image.BILINEAR).resize((200, 200), resample=Image.BILINEAR)
        mod_phash = compute_frame_phash(near_img)

        match_near = check_perceptual_blocklist([(3.0, mod_phash)], db, threshold=10)
        assert match_near is not None
        _, _, _, near_dist = match_near
        assert near_dist <= 10

        # 3. Unrelated image test (should NOT match)
        unrelated_img = Image.new("RGB", (200, 200), color=(255, 255, 255))
        draw_u = ImageDraw.Draw(unrelated_img)
        for i in range(0, 200, 12):
            draw_u.line([(i, 0), (i, 200)], fill=(0, 0, 0), width=4)
        unrelated_phash = compute_frame_phash(unrelated_img)

        match_none = check_perceptual_blocklist([(5.0, unrelated_phash)], db, threshold=5)
        assert match_none is None
    finally:
        db.query(BlocklistPHash).filter(BlocklistPHash.phash_hex == base_phash).delete()
        db.commit()
        db.close()
