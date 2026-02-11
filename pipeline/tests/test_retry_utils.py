"""Tests for retry_utils.py"""

import pytest
import time
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

from pipeline.retry_utils import (
    RetryConfig,
    NonRetryableError,
    MaxRetriesExceeded,
    _is_retryable_error,
    with_retry,
)


def test_retry_config_defaults():
    """Test RetryConfig default values."""
    config = RetryConfig()
    assert config.max_attempts == 3
    assert config.initial_delay == 1.0
    assert config.max_delay == 30.0
    assert config.backoff_multiplier == 2.0


def test_retry_config_custom():
    """Test RetryConfig with custom values."""
    config = RetryConfig(
        max_attempts=5,
        initial_delay=2.0,
        max_delay=60.0,
        backoff_multiplier=3.0
    )
    assert config.max_attempts == 5
    assert config.initial_delay == 2.0
    assert config.max_delay == 60.0
    assert config.backoff_multiplier == 3.0


def test_is_retryable_error_network_error():
    """Test that network errors are retryable."""
    error = URLError("Connection failed")
    assert _is_retryable_error(error) is True


def test_is_retryable_error_http_429():
    """Test that HTTP 429 (rate limit) is retryable."""
    error = HTTPError("url", 429, "Too Many Requests", {}, None)
    assert _is_retryable_error(error) is True


def test_is_retryable_error_http_500():
    """Test that HTTP 5xx errors are retryable."""
    for code in [500, 502, 503, 504]:
        error = HTTPError("url", code, "Server Error", {}, None)
        assert _is_retryable_error(error) is True


def test_is_retryable_error_http_400():
    """Test that HTTP 400 errors are NOT retryable."""
    for code in [400, 401, 403, 404]:
        error = HTTPError("url", code, "Client Error", {}, None)
        assert _is_retryable_error(error) is False


def test_is_retryable_error_generic():
    """Test that generic errors are NOT retryable."""
    error = ValueError("Generic error")
    assert _is_retryable_error(error) is False


def test_with_retry_success_first_attempt():
    """Test successful operation on first attempt."""
    mock_op = Mock(return_value="success")
    config = RetryConfig(max_attempts=3)

    result = with_retry(mock_op, config, "test_operation")

    assert result == "success"
    assert mock_op.call_count == 1


def test_with_retry_success_after_retries():
    """Test successful operation after retries."""
    mock_op = Mock(side_effect=[
        HTTPError("url", 503, "Service Unavailable", {}, None),
        HTTPError("url", 503, "Service Unavailable", {}, None),
        "success"
    ])
    config = RetryConfig(max_attempts=3, initial_delay=0.01)

    result = with_retry(mock_op, config, "test_operation")

    assert result == "success"
    assert mock_op.call_count == 3


def test_with_retry_non_retryable_error():
    """Test that non-retryable errors raise immediately."""
    mock_op = Mock(side_effect=HTTPError("url", 400, "Bad Request", {}, None))
    config = RetryConfig(max_attempts=3)

    with pytest.raises(NonRetryableError) as exc_info:
        with_retry(mock_op, config, "test_operation")

    assert "test_operation failed" in str(exc_info.value)
    assert mock_op.call_count == 1  # Only one attempt


def test_with_retry_max_retries_exceeded():
    """Test that max retries exceeded raises error."""
    mock_op = Mock(side_effect=HTTPError("url", 503, "Service Unavailable", {}, None))
    config = RetryConfig(max_attempts=3, initial_delay=0.01)

    with pytest.raises(MaxRetriesExceeded) as exc_info:
        with_retry(mock_op, config, "test_operation")

    assert "failed after 3 attempts" in str(exc_info.value)
    assert mock_op.call_count == 3


def test_with_retry_exponential_backoff():
    """Test exponential backoff timing."""
    call_times = []

    def failing_operation():
        call_times.append(time.time())
        raise HTTPError("url", 503, "Service Unavailable", {}, None)

    config = RetryConfig(max_attempts=3, initial_delay=0.05, backoff_multiplier=2.0)

    with pytest.raises(MaxRetriesExceeded):
        with_retry(failing_operation, config, "test_operation")

    # Check that delays increased (roughly)
    assert len(call_times) == 3
    delay1 = call_times[1] - call_times[0]
    delay2 = call_times[2] - call_times[1]

    # Second delay should be roughly 2x first delay (exponential backoff)
    assert delay2 > delay1


def test_with_retry_max_delay_cap():
    """Test that delays are capped at max_delay."""
    call_times = []

    def failing_operation():
        call_times.append(time.time())
        raise HTTPError("url", 503, "Service Unavailable", {}, None)

    config = RetryConfig(
        max_attempts=4,
        initial_delay=0.1,
        max_delay=0.15,  # Cap at 0.15s
        backoff_multiplier=2.0
    )

    with pytest.raises(MaxRetriesExceeded):
        with_retry(failing_operation, config, "test_operation")

    # Check that no delay exceeds max_delay
    for i in range(1, len(call_times)):
        delay = call_times[i] - call_times[i-1]
        assert delay <= 0.2  # Allow some tolerance


def test_with_retry_default_config():
    """Test with_retry using default config."""
    mock_op = Mock(return_value="success")

    result = with_retry(mock_op, operation_name="test")

    assert result == "success"
    assert mock_op.call_count == 1


def test_with_retry_preserves_return_type():
    """Test that return types are preserved."""
    # Test different return types
    assert with_retry(lambda: 42, operation_name="int") == 42
    assert with_retry(lambda: "text", operation_name="str") == "text"
    assert with_retry(lambda: {"key": "value"}, operation_name="dict") == {"key": "value"}
    assert with_retry(lambda: [1, 2, 3], operation_name="list") == [1, 2, 3]
