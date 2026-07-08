"""Logging decorators."""

import functools
import time
import uuid
from collections.abc import Callable
from typing import Any, TypeVar

from loguru import logger

F = TypeVar("F", bound=Callable[..., Any])


def timed(operation: str) -> Callable[[F], F]:
    """Decorator to time an operation and log its start and completion.

    Injects a correlation_id, operation name, and duration_ms into the log context.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            correlation_id = str(uuid.uuid4())
            context_logger = logger.bind(operation=operation, correlation_id=correlation_id)

            context_logger.debug(f"Starting {operation}")
            start_time = time.perf_counter()

            try:
                result = func(*args, **kwargs)

                duration_ms = (time.perf_counter() - start_time) * 1000
                context_logger.bind(duration_ms=duration_ms).debug(
                    f"Completed {operation} in {duration_ms:.2f}ms"
                )
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                context_logger.bind(duration_ms=duration_ms).error(
                    f"Failed {operation} after {duration_ms:.2f}ms: {e}"
                )
                raise

        return wrapper  # type: ignore

    return decorator
