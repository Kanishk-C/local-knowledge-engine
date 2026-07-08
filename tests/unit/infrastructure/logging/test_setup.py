"""Tests for logging setup."""

from loguru import logger

from lke.infrastructure.logging.setup import setup_logging


def test_setup_logging_dev_mode() -> None:
    """Test that dev logging configures without errors."""
    # We just ensure it doesn't crash and configures a handler
    # Since we can't easily inspect loguru handlers, we test execution
    setup_logging(level="DEBUG", is_dev=True)
    logger.debug("Test dev mode")


def test_setup_logging_json_mode() -> None:
    """Test that JSON logging configures without errors."""
    setup_logging(level="INFO", is_dev=False)
    logger.info("Test json mode")
