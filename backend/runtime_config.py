from __future__ import annotations

import os
from typing import Mapping

from backend.storage import _config as storage_config


INLINE_TRUE_VALUES = {"1", "true", "yes", "on"}


def _require_positive_int(env: Mapping[str, str], name: str, default: int) -> None:
    raw_value = env.get(name, str(default)).strip()
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc
    if parsed <= 0:
        raise RuntimeError(f"{name} must be a positive integer.")


def _is_inline_jobs_enabled(env: Mapping[str, str]) -> bool:
    return env.get("PLC_INLINE_JOBS", "").strip().lower() in INLINE_TRUE_VALUES


def validate_runtime_environment(mode: str, env: Mapping[str, str] | None = None) -> None:
    active_env = env or os.environ

    errors: list[str] = []
    database_url = active_env.get("DATABASE_URL", "").strip()
    if not database_url:
        errors.append("DATABASE_URL must be set.")

    redis_url = active_env.get("REDIS_URL", "redis://localhost:6379/0").strip()
    inline_jobs = _is_inline_jobs_enabled(active_env)
    if mode == "worker" or not inline_jobs:
        if not redis_url:
            errors.append("REDIS_URL must be set when queue-backed jobs are enabled.")

    try:
        storage_config(active_env)
    except RuntimeError as exc:
        errors.append(str(exc))

    for env_name, default in (
        ("PLC_WRITE_RATE_LIMIT_MAX_REQUESTS", 60),
        ("PLC_WRITE_RATE_LIMIT_WINDOW_SEC", 60),
        ("PLC_IDEMPOTENCY_TTL_SEC", 3600),
    ):
        try:
            _require_positive_int(active_env, env_name, default)
        except RuntimeError as exc:
            errors.append(str(exc))

    if errors:
        error_lines = "\n- ".join(errors)
        raise RuntimeError(f"Invalid runtime environment for {mode}:\n- {error_lines}")
