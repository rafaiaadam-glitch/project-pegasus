from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Mapping, Optional


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


def _validate_config(config: StorageConfig) -> None:
    if config.mode not in {"local", "s3", "gcs"}:
        raise RuntimeError("STORAGE_MODE must be either 'local', 's3', or 'gcs'.")

    if config.mode == "s3":
        if not config.s3_bucket:
            raise RuntimeError("S3_BUCKET must be set for S3 storage.")
        if not config.s3_prefix:
            raise RuntimeError("S3_PREFIX must be a non-empty path segment for S3 storage.")

    if config.mode == "gcs":
        if not config.gcs_bucket:
            raise RuntimeError("GCS_BUCKET must be set for GCS storage.")
        if not config.gcs_prefix:
            raise RuntimeError("GCS_PREFIX must be a non-empty path segment for GCS storage.")


def _config(env: Mapping[str, str] | None = None) -> StorageConfig:
    active_env = env or os.environ
    mode = active_env.get("STORAGE_MODE", "local")
    local_dir = Path(active_env.get("PLC_STORAGE_DIR", "storage")).resolve()
    config = StorageConfig(
        mode=mode,
        local_dir=local_dir,
        s3_bucket=active_env.get("S3_BUCKET"),
        s3_prefix=active_env.get("S3_PREFIX", "pegasus"),
        s3_endpoint_url=active_env.get("S3_ENDPOINT_URL"),
        s3_region=active_env.get("AWS_REGION") or active_env.get("S3_REGION"),
        gcs_bucket=active_env.get("GCS_BUCKET"),
        gcs_prefix=active_env.get("GCS_PREFIX", "pegasus"),
    )
    _validate_config(config)
    return config


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


def _copy_with_limit(fileobj: BinaryIO, handle: BinaryIO, max_bytes: Optional[int] = None) -> int:
    total = 0
    while True:
        chunk = fileobj.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if max_bytes is not None and total > max_bytes:
            raise ValueError(f"Audio file exceeds upload limit of {max_bytes} bytes.")
        handle.write(chunk)
    return total


def save_audio(fileobj: BinaryIO, filename: str, max_bytes: Optional[int] = None) -> str:
    cfg = _config()
    if cfg.mode == "s3":
        if max_bytes is not None:
            # Enforce size limit consistently in both local and S3 modes.
            import io

            buffer = io.BytesIO()
            _copy_with_limit(fileobj, buffer, max_bytes=max_bytes)
            buffer.seek(0)
            fileobj = buffer
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
        _copy_with_limit(fileobj, handle, max_bytes=max_bytes)
    return str(target)


def save_document(fileobj: BinaryIO, filename: str, max_bytes: Optional[int] = None) -> str:
    """
    Save a document file (e.g., PDF) to storage.

    Args:
        fileobj: File object to save
        filename: Name to save the file as
        max_bytes: Optional maximum file size in bytes

    Returns:
        Storage path (local path, s3://, or gs:// URL)
    """
    cfg = _config()
    if cfg.mode == "s3":
        if max_bytes is not None:
            import io

            buffer = io.BytesIO()
            _copy_with_limit(fileobj, buffer, max_bytes=max_bytes)
            buffer.seek(0)
            fileobj = buffer
        key = f"{cfg.s3_prefix}/documents/{filename}"
        _s3_client().upload_fileobj(fileobj, cfg.s3_bucket, key)
        return f"s3://{cfg.s3_bucket}/{key}"
    elif cfg.mode == "gcs":
        if not cfg.gcs_bucket:
            raise RuntimeError("GCS_BUCKET must be set for GCS storage.")
        blob_name = f"{cfg.gcs_prefix}/documents/{filename}"
        bucket = _gcs_client().bucket(cfg.gcs_bucket)
        blob = bucket.blob(blob_name)
        blob.upload_from_file(fileobj)
        return f"gs://{cfg.gcs_bucket}/{blob_name}"
    target = _local_path("documents", filename)
    with target.open("wb") as handle:
        _copy_with_limit(fileobj, handle, max_bytes=max_bytes)
    return str(target)


def save_transcript(payload: str, filename: str) -> str:
    cfg = _config()
    if cfg.mode == "s3":
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


def delete_storage_path(storage_path: str) -> bool:
    """Delete an artifact/export/audio path from local, S3, or GCS storage."""
    if not storage_path:
        return False

    if storage_path.startswith("s3://"):
        _, _, rest = storage_path.partition("s3://")
        bucket, _, key = rest.partition("/")
        if not bucket or not key:
            return False
        _s3_client().delete_object(Bucket=bucket, Key=key)
        return True

    if storage_path.startswith("gs://"):
        _, _, rest = storage_path.partition("gs://")
        bucket_name, _, blob_name = rest.partition("/")
        if not bucket_name or not blob_name:
            return False
        bucket = _gcs_client().bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.delete()
        return True

    path = Path(storage_path)
    if not path.exists():
        return False
    if path.is_file():
        path.unlink()
        return True
    shutil.rmtree(path)
    return True





def storage_path_exists(storage_path: str) -> bool:
    """Check whether a storage path exists in local, S3, or GCS storage."""
    if not storage_path:
        return False

    if storage_path.startswith("s3://"):
        _, _, rest = storage_path.partition("s3://")
        bucket, _, key = rest.partition("/")
        if not bucket or not key:
            return False
        try:
            _s3_client().head_object(Bucket=bucket, Key=key)
            return True
        except Exception:
            return False

    if storage_path.startswith("gs://"):
        _, _, rest = storage_path.partition("gs://")
        bucket_name, _, blob_name = rest.partition("/")
        if not bucket_name or not blob_name:
            return False
        try:
            bucket = _gcs_client().bucket(bucket_name)
            blob = bucket.blob(blob_name)
            return bool(blob.exists())
        except Exception:
            return False

    return Path(storage_path).exists()

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

def generate_upload_signed_url(
    filename: str,
    content_type: str,
    expires_in: int = 900,
    prefix: str = "uploads",
) -> dict[str, str]:
    """
    Generate a signed URL for direct file upload.

    Args:
        filename: Target filename
        content_type: MIME type of the file
        expires_in: Expiration time in seconds (default 15 minutes)
        prefix: Storage prefix (folder)

    Returns:
        Dictionary with 'url' (for PUT request) and 'storagePath' (to save in DB)
    """
    cfg = _config()
    
    if cfg.mode == "gcs":
        if not cfg.gcs_bucket:
            raise RuntimeError("GCS_BUCKET must be set for GCS storage.")
        
        from datetime import timedelta
        import google.auth
        from google.auth.transport import requests
        
        blob_name = f"{cfg.gcs_prefix}/{prefix}/{filename}"
        bucket = _gcs_client().bucket(cfg.gcs_bucket)
        blob = bucket.blob(blob_name)
        
        credentials, _ = google.auth.default()
        request = requests.Request()
        try:
            credentials.refresh(request)
        except Exception:
            pass

        token = credentials.token
        # Manual URL construction to bypass signing complexity
        from urllib.parse import quote
        encoded_blob_path = quote(blob_name)
        url = f"https://storage.googleapis.com/{cfg.gcs_bucket}/{encoded_blob_path}?access_token={token}"

        return {
            "url": url,
            "storagePath": f"gs://{cfg.gcs_bucket}/{blob_name}",
        }
    elif cfg.mode == "s3":
        key = f"{cfg.s3_prefix}/{prefix}/{filename}"
        url = _s3_client().generate_presigned_url(
            "put_object",
            Params={
                "Bucket": cfg.s3_bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
        )
        return {
            "url": url,
            "storagePath": f"s3://{cfg.s3_bucket}/{key}",
        }

    else:
        # Local mode fallback (not a signed URL, but a direct API path maybe? or just unsupported)
        # For local dev, signed URLs don't make sense unless we mock them.
        # We'll throw an error because the frontend expects to PUT to this URL.
        raise NotImplementedError("Direct uploads (signed URLs) not supported in local storage mode.")
