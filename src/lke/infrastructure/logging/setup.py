"""Logging setup and configuration."""

import sys

from loguru import logger


def setup_logging(level: str = "INFO", is_dev: bool = True) -> None:
    """Configure loguru with appropriate handlers.

    Args:
        level: The minimum logging level to output.
        is_dev: If True, uses human-readable colored output.
                If False, uses structured JSON output suitable for log aggregation.
    """
    # Remove default handler
    logger.remove()

    # Define custom formats
    dev_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "{message} {extra}"
    )

    if is_dev:
        logger.add(
            sys.stdout,
            level=level.upper(),
            format=dev_format,
            colorize=True,
            enqueue=True,
        )
    else:
        logger.add(
            sys.stdout,
            level=level.upper(),
            format="{message}",
            serialize=True,
            enqueue=True,
        )
