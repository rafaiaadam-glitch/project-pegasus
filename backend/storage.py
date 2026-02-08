from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Optional


@dataclass(frozen=True)
class StorageConfig:
    mode: str
    local_dir: Path
    s3_bucket: Optional[str]
    s3_prefix: Optional[str]


def _config() -> StorageConfig:
    mode = os.getenv("STORAGE_MODE", "local")
    local_dir = Path(os.getenv("PLC_STORAGE_DIR", "storage")).resolve()
    return StorageConfig(
        mode=mode,
        local_dir=local_dir,
        s3_bucket=os.getenv("S3_BUCKET"),
        s3_prefix=os.getenv("S3_PREFIX", "pegasus"),
    )


def _local_path(category: str, filename: str) -> Path:
    cfg = _config()
    target = cfg.local_dir / category / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def save_audio(fileobj: BinaryIO, filename: str) -> str:
    cfg = _config()
    if cfg.mode == "s3":
        import boto3

        if not cfg.s3_bucket:
            raise RuntimeError("S3_BUCKET must be set for S3 storage.")
        key = f"{cfg.s3_prefix}/audio/{filename}"
        boto3.client("s3").upload_fileobj(fileobj, cfg.s3_bucket, key)
        return f"s3://{cfg.s3_bucket}/{key}"
    target = _local_path("audio", filename)
    with target.open("wb") as handle:
        shutil.copyfileobj(fileobj, handle)
    return str(target)


def save_transcript(payload: str, filename: str) -> str:
    cfg = _config()
    if cfg.mode == "s3":
        import boto3

        if not cfg.s3_bucket:
            raise RuntimeError("S3_BUCKET must be set for S3 storage.")
        key = f"{cfg.s3_prefix}/transcripts/{filename}"
        boto3.client("s3").put_object(
            Bucket=cfg.s3_bucket, Key=key, Body=payload.encode("utf-8")
        )
        return f"s3://{cfg.s3_bucket}/{key}"
    target = _local_path("transcripts", filename)
    target.write_text(payload, encoding="utf-8")
    return str(target)


def save_export(payload: bytes, filename: str) -> str:
    cfg = _config()
    if cfg.mode == "s3":
        import boto3

        if not cfg.s3_bucket:
            raise RuntimeError("S3_BUCKET must be set for S3 storage.")
        key = f"{cfg.s3_prefix}/exports/{filename}"
        boto3.client("s3").put_object(Bucket=cfg.s3_bucket, Key=key, Body=payload)
        return f"s3://{cfg.s3_bucket}/{key}"
    target = _local_path("exports", filename)
    target.write_bytes(payload)
    return str(target)


def save_artifact_file(source: Path, filename: str) -> str:
    cfg = _config()
    if cfg.mode == "s3":
        import boto3

        if not cfg.s3_bucket:
            raise RuntimeError("S3_BUCKET must be set for S3 storage.")
        key = f"{cfg.s3_prefix}/artifacts/{filename}"
        boto3.client("s3").upload_file(str(source), cfg.s3_bucket, key)
        return f"s3://{cfg.s3_bucket}/{key}"
    target = _local_path("artifacts", filename)
    target.write_bytes(source.read_bytes())
    return str(target)


def save_export_file(source: Path, filename: str) -> str:
    cfg = _config()
    if cfg.mode == "s3":
        import boto3

        if not cfg.s3_bucket:
            raise RuntimeError("S3_BUCKET must be set for S3 storage.")
        key = f"{cfg.s3_prefix}/exports/{filename}"
        boto3.client("s3").upload_file(str(source), cfg.s3_bucket, key)
        return f"s3://{cfg.s3_bucket}/{key}"
    target = _local_path("exports", filename)
    target.write_bytes(source.read_bytes())
    return str(target)


def download_url(storage_path: str, expires_in: int = 900) -> Optional[str]:
    if not storage_path.startswith("s3://"):
        return None
    _, _, rest = storage_path.partition("s3://")
    bucket, _, key = rest.partition("/")
    if not bucket or not key:
        return None
    import boto3

    client = boto3.client("s3")
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )
