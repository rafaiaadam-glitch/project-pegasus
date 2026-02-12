from __future__ import annotations

import json
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
    s3_endpoint_url: Optional[str]
    s3_region: Optional[str]
    gcs_bucket: Optional[str]
    gcs_prefix: Optional[str]


def _config() -> StorageConfig:
    mode = os.getenv("STORAGE_MODE", "local")
    local_dir = Path(os.getenv("PLC_STORAGE_DIR", "storage")).resolve()
    return StorageConfig(
        mode=mode,
        local_dir=local_dir,
        s3_bucket=os.getenv("S3_BUCKET"),
        s3_prefix=os.getenv("S3_PREFIX", "pegasus"),
        s3_endpoint_url=os.getenv("S3_ENDPOINT_URL"),
        s3_region=os.getenv("AWS_REGION") or os.getenv("S3_REGION"),
        gcs_bucket=os.getenv("GCS_BUCKET"),
        gcs_prefix=os.getenv("GCS_PREFIX", "pegasus"),
    )


def _s3_client():
    cfg = _config()
    import boto3

    return boto3.client(
        "s3",
        region_name=cfg.s3_region,
        endpoint_url=cfg.s3_endpoint_url,
    )


def _gcs_client():
    from google.cloud import storage
    return storage.Client()


def _local_path(category: str, filename: str) -> Path:
    cfg = _config()
    target = cfg.local_dir / category / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def save_audio(fileobj: BinaryIO, filename: str) -> str:
    cfg = _config()
    if cfg.mode == "s3":
        if not cfg.s3_bucket:
            raise RuntimeError("S3_BUCKET must be set for S3 storage.")
        key = f"{cfg.s3_prefix}/audio/{filename}"
        _s3_client().upload_fileobj(fileobj, cfg.s3_bucket, key)
        return f"s3://{cfg.s3_bucket}/{key}"
    elif cfg.mode == "gcs":
        if not cfg.gcs_bucket:
            raise RuntimeError("GCS_BUCKET must be set for GCS storage.")
        blob_name = f"{cfg.gcs_prefix}/audio/{filename}"
        bucket = _gcs_client().bucket(cfg.gcs_bucket)
        blob = bucket.blob(blob_name)
        blob.upload_from_file(fileobj)
        return f"gs://{cfg.gcs_bucket}/{blob_name}"
    target = _local_path("audio", filename)
    with target.open("wb") as handle:
        shutil.copyfileobj(fileobj, handle)
    return str(target)


def save_transcript(payload: str, filename: str) -> str:
    cfg = _config()
    if cfg.mode == "s3":
        if not cfg.s3_bucket:
            raise RuntimeError("S3_BUCKET must be set for S3 storage.")
        key = f"{cfg.s3_prefix}/transcripts/{filename}"
        _s3_client().put_object(
            Bucket=cfg.s3_bucket, Key=key, Body=payload.encode("utf-8")
        )
        return f"s3://{cfg.s3_bucket}/{key}"
    elif cfg.mode == "gcs":
        if not cfg.gcs_bucket:
            raise RuntimeError("GCS_BUCKET must be set for GCS storage.")
        blob_name = f"{cfg.gcs_prefix}/transcripts/{filename}"
        bucket = _gcs_client().bucket(cfg.gcs_bucket)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(payload, content_type="text/plain")
        return f"gs://{cfg.gcs_bucket}/{blob_name}"
    target = _local_path("transcripts", filename)
    target.write_text(payload, encoding="utf-8")
    return str(target)


def save_export(payload: bytes, filename: str) -> str:
    cfg = _config()
    if cfg.mode == "s3":
        if not cfg.s3_bucket:
            raise RuntimeError("S3_BUCKET must be set for S3 storage.")
        key = f"{cfg.s3_prefix}/exports/{filename}"
        _s3_client().put_object(Bucket=cfg.s3_bucket, Key=key, Body=payload)
        return f"s3://{cfg.s3_bucket}/{key}"
    elif cfg.mode == "gcs":
        if not cfg.gcs_bucket:
            raise RuntimeError("GCS_BUCKET must be set for GCS storage.")
        blob_name = f"{cfg.gcs_prefix}/exports/{filename}"
        bucket = _gcs_client().bucket(cfg.gcs_bucket)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(payload)
        return f"gs://{cfg.gcs_bucket}/{blob_name}"
    target = _local_path("exports", filename)
    target.write_bytes(payload)
    return str(target)


def save_artifact_file(source: Path, filename: str) -> str:
    cfg = _config()
    if cfg.mode == "s3":
        if not cfg.s3_bucket:
            raise RuntimeError("S3_BUCKET must be set for S3 storage.")
        key = f"{cfg.s3_prefix}/artifacts/{filename}"
        _s3_client().upload_file(str(source), cfg.s3_bucket, key)
        return f"s3://{cfg.s3_bucket}/{key}"
    elif cfg.mode == "gcs":
        if not cfg.gcs_bucket:
            raise RuntimeError("GCS_BUCKET must be set for GCS storage.")
        blob_name = f"{cfg.gcs_prefix}/artifacts/{filename}"
        bucket = _gcs_client().bucket(cfg.gcs_bucket)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(str(source))
        return f"gs://{cfg.gcs_bucket}/{blob_name}"
    target = _local_path("artifacts", filename)
    target.write_bytes(source.read_bytes())
    return str(target)


def save_export_file(source: Path, filename: str) -> str:
    cfg = _config()
    if cfg.mode == "s3":
        if not cfg.s3_bucket:
            raise RuntimeError("S3_BUCKET must be set for S3 storage.")
        key = f"{cfg.s3_prefix}/exports/{filename}"
        _s3_client().upload_file(str(source), cfg.s3_bucket, key)
        return f"s3://{cfg.s3_bucket}/{key}"
    elif cfg.mode == "gcs":
        if not cfg.gcs_bucket:
            raise RuntimeError("GCS_BUCKET must be set for GCS storage.")
        blob_name = f"{cfg.gcs_prefix}/exports/{filename}"
        bucket = _gcs_client().bucket(cfg.gcs_bucket)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(str(source))
        return f"gs://{cfg.gcs_bucket}/{blob_name}"
    target = _local_path("exports", filename)
    target.write_bytes(source.read_bytes())
    return str(target)


def download_url(storage_path: str, expires_in: int = 900) -> Optional[str]:
    if storage_path.startswith("s3://"):
        _, _, rest = storage_path.partition("s3://")
        bucket, _, key = rest.partition("/")
        if not bucket or not key:
            return None
        return _s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )
    elif storage_path.startswith("gs://"):
        from datetime import timedelta
        _, _, rest = storage_path.partition("gs://")
        bucket_name, _, blob_name = rest.partition("/")
        if not bucket_name or not blob_name:
            return None
        bucket = _gcs_client().bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.generate_signed_url(expiration=timedelta(seconds=expires_in))
    return None



def load_json_payload(storage_path: str) -> dict:
    """Load a JSON payload from local, S3, or GCS storage."""
    if storage_path.startswith("s3://"):
        _, _, rest = storage_path.partition("s3://")
        bucket, _, key = rest.partition("/")
        if not bucket or not key:
            raise FileNotFoundError("Invalid S3 storage path.")
        response = _s3_client().get_object(Bucket=bucket, Key=key)
        body = response["Body"].read().decode("utf-8")
        return json.loads(body)
    elif storage_path.startswith("gs://"):
        _, _, rest = storage_path.partition("gs://")
        bucket_name, _, blob_name = rest.partition("/")
        if not bucket_name or not blob_name:
            raise FileNotFoundError("Invalid GCS storage path.")
        bucket = _gcs_client().bucket(bucket_name)
        blob = bucket.blob(blob_name)
        body = blob.download_as_text()
        return json.loads(body)

    path = Path(storage_path)
    if not path.exists():
        raise FileNotFoundError(f"Storage path not found: {storage_path}")
    return json.loads(path.read_text(encoding="utf-8"))
