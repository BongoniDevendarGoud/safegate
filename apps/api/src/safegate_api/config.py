"""
SafeGate Configuration Subsystem.
Loads hierarchical settings from YAML and Environment Variables with Pydantic v2 validation.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerConfig(BaseModel):
    host: str = Field(default="0.0.0.0", description="API server bind host")
    port: int = Field(default=8000, ge=1, le=65535, description="API server bind port")
    workers: int = Field(default=4, ge=1, description="Uvicorn worker count")
    api_prefix: str = Field(default="/v1", description="Global versioned API prefix")


class DatabaseConfig(BaseModel):
    url: str = Field(
        default="postgresql+asyncpg://safegate_user:safegate_secret_pass@localhost:5432/safegate",
        description="Async PostgreSQL connection URI",
    )
    pool_size: int = Field(default=20, ge=1, le=100)
    max_overflow: int = Field(default=10, ge=0)
    echo: bool = Field(default=False)


class RedisConfig(BaseModel):
    url: str = Field(default="redis://localhost:6379/0", description="Redis connection URI")
    queue_name: str = Field(default="safegate:upload_jobs")
    dead_letter_queue: str = Field(default="safegate:upload_jobs:dlq")


class StorageConfig(BaseModel):
    endpoint_url: str = Field(default="http://localhost:9000", description="S3/MinIO endpoint")
    access_key: str = Field(default="minioadmin")
    secret_key: str = Field(default="minioadmin123")
    region_name: str = Field(default="us-east-1")
    quarantine_bucket: str = Field(default="safegate-quarantine")
    public_bucket: str = Field(default="safegate-public")
    restricted_legal_bucket: str = Field(default="safegate-restricted-legal")
    secure_ssl: bool = Field(default=False)


class LimitsConfig(BaseModel):
    max_video_size_bytes: int = Field(default=524_288_000, gt=0)  # 500 MB
    max_image_size_bytes: int = Field(default=52_428_800, gt=0)  # 50 MB
    max_video_duration_seconds: int = Field(default=600, gt=0)  # 10 minutes
    max_frame_rate: int = Field(default=60, ge=1, le=240)
    max_resolution_width: int = Field(default=3840, ge=64, le=7680)
    max_resolution_height: int = Field(default=2160, ge=64, le=4320)
    decode_timeout_seconds: int = Field(default=120, gt=0)


class PolicyConfig(BaseModel):
    fail_closed_mode: bool = Field(
        default=True,
        description="Invariant: on model/worker/dependency failure, NEVER return ALLOW",
    )
    min_consecutive_red_frames: int = Field(
        default=2,
        ge=1,
        description="Temporal neighbor confirmation required to finalize RED block",
    )
    ensemble_agreement_threshold: float = Field(default=0.65, ge=0.0, le=1.0)


class ScoreThresholds(BaseModel):
    red_block_threshold: float = Field(default=0.78, ge=0.0, le=1.0)
    yellow_review_threshold: float = Field(default=0.45, ge=0.0, le=1.0)

    @field_validator("yellow_review_threshold")
    @classmethod
    def validate_threshold_ordering(cls, v: float, info: Any) -> float:
        values = info.data
        if "red_block_threshold" in values and v >= values["red_block_threshold"]:
            raise ValueError(
                "yellow_review_threshold must be strictly less than red_block_threshold"
            )
        return v


class SingleThreshold(BaseModel):
    yellow_review_threshold: float = Field(default=0.60, ge=0.0, le=1.0)


class ThresholdsConfig(BaseModel):
    deepfake_manipulation_score: ScoreThresholds = Field(default_factory=ScoreThresholds)
    sensitive_content_score: SingleThreshold = Field(
        default_factory=lambda: SingleThreshold(yellow_review_threshold=0.60)
    )
    uncertainty_score: SingleThreshold = Field(
        default_factory=lambda: SingleThreshold(yellow_review_threshold=0.40)
    )


class ChildSafetyConfig(BaseModel):
    hash_matching_enabled: bool = Field(default=True)
    partner_api_mock_mode: bool = Field(default=True)
    strict_escalation_only: bool = Field(default=True)
    auto_redact_thumbnails: bool = Field(default=True)


class AuditConfig(BaseModel):
    hmac_secret: str = Field(
        default="dev_audit_hmac_secret_key_change_in_production_32b",
        min_length=16,
        description="Secret key for HMAC-SHA256 audit ledger chaining",
    )
    chain_algorithm: str = Field(default="HMAC-SHA256")


class SafeGateConfig(BaseSettings):
    """
    Master SafeGate Configuration combining YAML file defaults and Environment Overrides.
    """

    model_config = SettingsConfigDict(
        env_prefix="SAFEGATE_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    server: ServerConfig = Field(default_factory=ServerConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
    child_safety: ChildSafetyConfig = Field(default_factory=ChildSafetyConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)

    @classmethod
    def load(cls, yaml_path: str | Path | None = None) -> SafeGateConfig:
        """
        Loads configuration from YAML path (or default location) with env var overrides.
        """
        data: dict[str, Any] = {}
        target_path: Path | None = None

        if yaml_path:
            target_path = Path(yaml_path)
        else:
            env_yaml = os.getenv("SAFEGATE_CONFIG_PATH")
            if env_yaml:
                target_path = Path(env_yaml)
            else:
                default_file = (
                    Path(__file__).resolve().parents[2] / "config" / "safegate.default.yaml"
                )
                if default_file.exists():
                    target_path = default_file

        if target_path and target_path.exists():
            with open(target_path, encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    data = loaded

        return cls(**data)


# Global singleton instance loaded once
settings = SafeGateConfig.load()


def load_config(yaml_path: str | Path | None = None) -> SafeGateConfig:
    """Convenience function to load SafeGateConfig from a specific path or defaults."""
    return SafeGateConfig.load(yaml_path=yaml_path)
