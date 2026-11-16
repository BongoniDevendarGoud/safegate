from pathlib import Path

import pytest
from pydantic import ValidationError

from safegate_api.config import (
    ScoreThresholds,
    load_config,
)


def test_default_config_loading() -> None:
    """Verify that default config loads correctly with valid defaults."""
    config = load_config()
    assert config.server.port == 8000
    assert config.policy.fail_closed_mode is True
    assert (
        config.thresholds.deepfake_manipulation_score.yellow_review_threshold
        < config.thresholds.deepfake_manipulation_score.red_block_threshold
    )
    assert config.limits.max_video_size_bytes == 524288000
    assert config.limits.max_image_size_bytes == 52428800


def test_threshold_validation_rejects_inverted_values() -> None:
    """Verify that yellow_review >= red_block triggers a ValidationError."""
    with pytest.raises(ValidationError):
        ScoreThresholds(yellow_review_threshold=0.8, red_block_threshold=0.5)


def test_threshold_validation_rejects_out_of_bounds() -> None:
    """Verify that scores outside [0.0, 1.0] are rejected."""
    with pytest.raises(ValidationError):
        ScoreThresholds(yellow_review_threshold=-0.1, red_block_threshold=0.8)

    with pytest.raises(ValidationError):
        ScoreThresholds(yellow_review_threshold=0.2, red_block_threshold=1.5)


def test_config_override_from_yaml(tmp_path: Path) -> None:
    """Verify loading from a custom YAML file."""
    yaml_content = """
server:
  port: 9090
limits:
  max_video_size_bytes: 104857600
policy:
  fail_closed_mode: true
"""
    config_file = tmp_path / "custom_config.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")

    config = load_config(yaml_path=config_file)
    assert config.server.port == 9090
    assert config.limits.max_video_size_bytes == 104857600
    assert config.policy.fail_closed_mode is True
