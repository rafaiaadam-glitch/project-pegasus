#!/usr/bin/env python3
"""Retry utilities with exponential backoff for handling transient failures."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, TypeVar
from urllib.error import HTTPError, URLError


T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    backoff_multiplier: float = 2.0


class NonRetryableError(Exception):
    """Exception raised when an error should not be retried."""

    pass


class MaxRetriesExceeded(Exception):
    """Exception raised when maximum retry attempts are exhausted."""

    pass


def _is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error should trigger a retry.

    Args:
        error: The exception to check

    Returns:
        True if the error is retryable (network issues, rate limits, server errors)
    """
    # Network/connection errors are retryable
    if isinstance(error, URLError) and not isinstance(error, HTTPError):
        return True

    # HTTP errors: check status code
    if isinstance(error, HTTPError):
        # Retry on rate limiting and server errors
        if error.code == 429:  # Too Many Requests
            return True
        if 500 <= error.code < 600:  # Server errors
            return True
        # Don't retry client errors (400, 401, 403, 404, etc.)
        return False

    # Other errors: don't retry by default
    return False


def with_retry(
    operation: Callable[[], T],
    config: Optional[RetryConfig] = None,
    operation_name: str = "operation",
) -> T:
    """
    Execute an operation with retry logic and exponential backoff.

    Args:
        operation: Function to execute (should take no arguments)
        config: Retry configuration (uses defaults if not provided)
        operation_name: Human-readable name for logging

    Returns:
        Result of the operation

    Raises:
        NonRetryableError: If a non-retryable error occurs
        MaxRetriesExceeded: If all retry attempts are exhausted
    """
    if config is None:
        config = RetryConfig()

    last_error: Optional[Exception] = None
    delay = config.initial_delay

    for attempt in range(1, config.max_attempts + 1):
        try:
            return operation()
        except Exception as e:
            last_error = e

            # Check if error is retryable
            if not _is_retryable_error(e):
                raise NonRetryableError(f"{operation_name} failed: {e}") from e

            # If this was the last attempt, don't wait
            if attempt >= config.max_attempts:
                break

            # Log retry attempt
            print(f"[Retry] {operation_name} attempt {attempt}/{config.max_attempts} failed: {e}")
            print(f"[Retry] Waiting {delay:.1f}s before retry...")

            # Wait with exponential backoff
            time.sleep(delay)
            delay = min(delay * config.backoff_multiplier, config.max_delay)

    # All retries exhausted
    error_msg = f"{operation_name} failed after {config.max_attempts} attempts"
    if last_error:
        error_msg += f": {last_error}"
    raise MaxRetriesExceeded(error_msg) from last_error
