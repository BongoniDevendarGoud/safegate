"""
SafeGate Storage Subsystem.
Enforces physical bucket separation for quarantine, public publication, and statutory vault.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import BinaryIO

from safegate_api.config import StorageConfig
from safegate_api.errors import QuarantineViolationError


class StorageClient:
    """
    Manages object storage operations with strict quarantine boundaries.
    """

    def __init__(self, config: StorageConfig, local_storage_dir: Path | None = None) -> None:
        self.config = config
        self.local_storage_dir = local_storage_dir
        if self.local_storage_dir:
            self.local_storage_dir.mkdir(parents=True, exist_ok=True)
            (self.local_storage_dir / "quarantine").mkdir(exist_ok=True)
            (self.local_storage_dir / "published").mkdir(exist_ok=True)
            (self.local_storage_dir / "vault").mkdir(exist_ok=True)

    def upload_quarantine(
        self,
        key: str,
        data: bytes | BinaryIO,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> str:
        """
        Uploads an unverified asset directly into the quarantine bucket.
        """
        raw_bytes = data if isinstance(data, bytes) else data.read()

        if self.local_storage_dir:
            dest = self.local_storage_dir / "quarantine" / key
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw_bytes)
            return f"local://quarantine/{key}"

        # Production / S3 path using boto3
        import boto3

        s3 = boto3.client(
            "s3",
            endpoint_url=self.config.endpoint_url,
            aws_access_key_id=self.config.access_key,
            aws_secret_access_key=self.config.secret_key,
            region_name=self.config.region_name,
        )
        s3.put_object(
            Bucket=self.config.quarantine_bucket,
            Key=key,
            Body=raw_bytes,
            ContentType=content_type,
            Metadata=metadata or {},
        )
        return f"s3://{self.config.quarantine_bucket}/{key}"

    def promote_to_published(self, key: str, allow_confirmed: bool) -> str:
        """
        Promotes an asset from quarantine to published bucket ONLY after ALLOW verdict.
        Guards against premature egress.
        """
        if not allow_confirmed:
            raise QuarantineViolationError(asset_id=key)

        if self.local_storage_dir:
            src = self.local_storage_dir / "quarantine" / key
            if not src.exists():
                raise FileNotFoundError(f"Quarantined asset {key} not found.")
            dest = self.local_storage_dir / "published" / key
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
            src.unlink(missing_ok=True)
            return f"local://published/{key}"

        import boto3

        s3 = boto3.client(
            "s3",
            endpoint_url=self.config.endpoint_url,
            aws_access_key_id=self.config.access_key,
            aws_secret_access_key=self.config.secret_key,
            region_name=self.config.region_name,
        )
        # Copy to published bucket
        s3.copy_object(
            CopySource={"Bucket": self.config.quarantine_bucket, "Key": key},
            Bucket=self.config.public_bucket,
            Key=key,
        )
        # Delete from quarantine
        s3.delete_object(Bucket=self.config.quarantine_bucket, Key=key)
        return f"s3://{self.config.public_bucket}/{key}"

    def escalate_to_vault(self, key: str) -> str:
        """
        Moves restricted statutory/CSAM evidence into an isolated, access-restricted vault bucket.
        """
        if self.local_storage_dir:
            src = self.local_storage_dir / "quarantine" / key
            dest = self.local_storage_dir / "vault" / key
            dest.parent.mkdir(parents=True, exist_ok=True)
            if src.exists():
                dest.write_bytes(src.read_bytes())
                # Secure shred / overwrite before delete
                src.write_bytes(b"\x00" * src.stat().st_size)
                src.unlink()
            return f"local://vault/{key}"

        import boto3

        s3 = boto3.client(
            "s3",
            endpoint_url=self.config.endpoint_url,
            aws_access_key_id=self.config.access_key,
            aws_secret_access_key=self.config.secret_key,
            region_name=self.config.region_name,
        )
        s3.copy_object(
            CopySource={"Bucket": self.config.quarantine_bucket, "Key": key},
            Bucket=self.config.restricted_legal_bucket,
            Key=key,
        )
        s3.delete_object(Bucket=self.config.quarantine_bucket, Key=key)
        return f"s3://{self.config.restricted_legal_bucket}/{key}"

    def get_quarantined_stream(self, key: str) -> BinaryIO:
        """
        Retrieves a stream of the quarantined object for worker processing.
        """
        if self.local_storage_dir:
            path = self.local_storage_dir / "quarantine" / key
            if not path.exists():
                raise FileNotFoundError(f"Quarantined asset {key} not found.")
            return io.BytesIO(path.read_bytes())

        import boto3

        s3 = boto3.client(
            "s3",
            endpoint_url=self.config.endpoint_url,
            aws_access_key_id=self.config.access_key,
            aws_secret_access_key=self.config.secret_key,
            region_name=self.config.region_name,
        )
        resp = s3.get_object(Bucket=self.config.quarantine_bucket, Key=key)
        return io.BytesIO(resp["Body"].read())

    def download_to_temp(self, key: str, temp_dir: Path | None = None) -> Path:
        """
        Extracts a quarantined asset to a local file path for inference/processing.
        """
        import tempfile

        t_dir = temp_dir or Path(tempfile.gettempdir())
        suffix = Path(key).suffix or ".bin"
        temp_file = t_dir / f"safegate_proc_{Path(key).name}_{suffix}"
        stream = self.get_quarantined_stream(key)
        temp_file.write_bytes(stream.read())
        return temp_file
