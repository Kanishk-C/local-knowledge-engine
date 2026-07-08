"""Tests for RetryPolicy."""

import pytest

from lke.infrastructure.resilience.retry import RetryPolicy


def test_retry_policy_success() -> None:
    """Test successful execution without retries."""

    def func() -> str:
        return "success"

    result = RetryPolicy.execute(func)
    assert result == "success"


def test_retry_policy_retries_and_succeeds() -> None:
    """Test that function is retried and succeeds."""
    attempts = 0

    def func() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ValueError("Temporary error")
        return "success"

    result = RetryPolicy.execute(
        func, max_retries=3, initial_backoff_ms=1, max_backoff_ms=2, exceptions=(ValueError,)
    )
    assert result == "success"
    assert attempts == 3


def test_retry_policy_fails_after_max_retries() -> None:
    """Test that function fails after exceeding max_retries."""
    attempts = 0

    def func() -> str:
        nonlocal attempts
        attempts += 1
        raise ValueError("Persistent error")

    with pytest.raises(ValueError, match="Persistent error"):
        RetryPolicy.execute(
            func, max_retries=2, initial_backoff_ms=1, max_backoff_ms=2, exceptions=(ValueError,)
        )
    assert attempts == 3


def test_retry_policy_ignores_unspecified_exceptions() -> None:
    """Test that unspecified exceptions are not caught."""
    attempts = 0

    def func() -> str:
        nonlocal attempts
        attempts += 1
        raise KeyError("Not caught")

    with pytest.raises(KeyError, match="Not caught"):
        RetryPolicy.execute(
            func, max_retries=3, initial_backoff_ms=1, max_backoff_ms=2, exceptions=(ValueError,)
        )
    assert attempts == 1
