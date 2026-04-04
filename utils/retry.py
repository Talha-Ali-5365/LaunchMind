"""Retry helpers for HTTP, LLM, and async agent calls."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


def with_retry(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay_s: float = 1.0,
    operation: str = "operation",
) -> T:
    """Run a zero-arg callable with exponential backoff retries.

    Args:
        fn: Callable to invoke.
        attempts: Maximum attempts before re-raising the last error.
        base_delay_s: Base delay; doubled each retry.
        operation: Label for log lines.

    Returns:
        The callable's return value.

    Raises:
        ValueError: If ``attempts < 1`` or ``base_delay_s`` is negative.
        Exception: The last exception if all attempts fail.
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    if base_delay_s < 0:
        raise ValueError("base_delay_s must be >= 0")
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            logger.warning("%s failed attempt %s/%s: %s", operation, i + 1, attempts, e)
            if i < attempts - 1:
                time.sleep(base_delay_s * (2**i))
    assert last_exc is not None
    raise last_exc


async def with_retry_async(
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay_s: float = 1.0,
    operation: str = "operation",
) -> T:
    """Run a zero-arg async callable with exponential backoff retries.

    Args:
        fn: Async callable to await.
        attempts: Maximum attempts before re-raising the last error.
        base_delay_s: Base delay; doubled each retry.
        operation: Label for log lines.

    Returns:
        The awaited return value.

    Raises:
        ValueError: If ``attempts < 1`` or ``base_delay_s`` is negative.
        Exception: The last exception if all attempts fail.
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    if base_delay_s < 0:
        raise ValueError("base_delay_s must be >= 0")
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return await fn()
        except Exception as e:
            last_exc = e
            logger.warning("%s async failed attempt %s/%s: %s", operation, i + 1, attempts, e)
            if i < attempts - 1:
                await asyncio.sleep(base_delay_s * (2**i))
    assert last_exc is not None
    raise last_exc
