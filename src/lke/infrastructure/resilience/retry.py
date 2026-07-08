"""Retry policy implementation for robust infrastructure calls."""

import random
import time
from collections.abc import Callable
from typing import TypeVar

from loguru import logger

T = TypeVar("T")


class RetryPolicy:
    """Executes a callable with exponential backoff and jitter."""

    @staticmethod
    def execute(
        func: Callable[[], T],
        max_retries: int = 3,
        initial_backoff_ms: int = 100,
        max_backoff_ms: int = 2000,
        exceptions: tuple[type[Exception], ...] = (Exception,),
    ) -> T:
        """Execute a function with retry logic.

        Args:
            func: The callable to execute.
            max_retries: Maximum number of retries before failing.
            initial_backoff_ms: Initial backoff duration in milliseconds.
            max_backoff_ms: Maximum backoff duration in milliseconds.
            exceptions: Tuple of exceptions to catch and retry on.

        Returns:
            The result of the callable.

        Raises:
            Exception: Re-raises the caught exception if max_retries is exceeded.
        """
        retries = 0
        backoff = initial_backoff_ms

        while True:
            try:
                return func()
            except exceptions as e:
                retries += 1
                if retries > max_retries:
                    logger.error(f"Action failed after {max_retries} retries: {e}")
                    raise

                jitter = random.uniform(0.8, 1.2)
                sleep_ms = min(backoff * jitter, max_backoff_ms)

                logger.warning(
                    f"Action failed (attempt {retries}/{max_retries}): {e}. "
                    f"Retrying in {sleep_ms:.0f}ms."
                )

                time.sleep(sleep_ms / 1000.0)
                backoff *= 2
