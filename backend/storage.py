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


def _validate_config(config: StorageConfig) -> None:
    if config.mode not in {"local", "s3"}:
        raise RuntimeError("STORAGE_MODE must be either 'local' or 's3'.")

    if config.mode == "s3":
        if not config.s3_bucket:
            raise RuntimeError("S3_BUCKET must be set for S3 storage.")
        if not config.s3_prefix:
            raise RuntimeError("S3_PREFIX must be a non-empty path segment for S3 storage.")


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
    target = _local_path("audio", filename)
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
    target = _local_path("transcripts", filename)
    target.write_text(payload, encoding="utf-8")
    return str(target)


def save_export(payload: bytes, filename: str) -> str:
    cfg = _config()
    if cfg.mode == "s3":
        key = f"{cfg.s3_prefix}/exports/{filename}"
        _s3_client().put_object(Bucket=cfg.s3_bucket, Key=key, Body=payload)
        return f"s3://{cfg.s3_bucket}/{key}"
    target = _local_path("exports", filename)
    target.write_bytes(payload)
    return str(target)


def save_artifact_file(source: Path, filename: str) -> str:
    cfg = _config()
    if cfg.mode == "s3":
        key = f"{cfg.s3_prefix}/artifacts/{filename}"
        _s3_client().upload_file(str(source), cfg.s3_bucket, key)
        return f"s3://{cfg.s3_bucket}/{key}"
    target = _local_path("artifacts", filename)
    target.write_bytes(source.read_bytes())
    return str(target)


def save_export_file(source: Path, filename: str) -> str:
    cfg = _config()
    if cfg.mode == "s3":
        key = f"{cfg.s3_prefix}/exports/{filename}"
        _s3_client().upload_file(str(source), cfg.s3_bucket, key)
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
    return _s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )



def load_json_payload(storage_path: str) -> dict:
    """Load a JSON payload from local or S3-backed storage."""
    if storage_path.startswith("s3://"):
        _, _, rest = storage_path.partition("s3://")
        bucket, _, key = rest.partition("/")
        if not bucket or not key:
            raise FileNotFoundError("Invalid S3 storage path.")
        response = _s3_client().get_object(Bucket=bucket, Key=key)
        body = response["Body"].read().decode("utf-8")
        return json.loads(body)

    path = Path(storage_path)
    if not path.exists():
        raise FileNotFoundError(f"Storage path not found: {storage_path}")
    return json.loads(path.read_text(encoding="utf-8"))
