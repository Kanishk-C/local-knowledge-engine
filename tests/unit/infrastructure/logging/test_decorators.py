"""Tests for logging decorators."""

import pytest

from lke.infrastructure.logging.decorators import timed


def test_timed_decorator_success() -> None:
    """Test the @timed decorator on a successful function."""

    @timed(operation="test_success")
    def dummy_func(x: int) -> int:
        return x * 2

    # We just test that the function still works and doesn't crash
    # To properly test loguru output, we would need to capture the logs,
    # but for simple unit tests, this verifies the decorator signature and logic
    # doesn't interfere with the return value.
    assert dummy_func(21) == 42


def test_timed_decorator_failure() -> None:
    """Test the @timed decorator on a failing function."""

    @timed(operation="test_failure")
    def dummy_func_fail() -> None:
        raise ValueError("Intentional failure")

    with pytest.raises(ValueError, match="Intentional failure"):
        dummy_func_fail()
