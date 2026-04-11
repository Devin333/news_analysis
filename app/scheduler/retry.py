"""Retry utilities for scheduler jobs."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from app.bootstrap.logging import get_logger
from app.scheduler.models import RetryPolicy

logger = get_logger(__name__)

T = TypeVar("T")


async def with_retry(
    func: Callable[..., Awaitable[T]],
    policy: RetryPolicy,
    *args: Any,
    **kwargs: Any,
) -> T:
    """Execute async function with retry policy."""
    last_error: Exception | None = None

    for attempt in range(policy.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < policy.max_retries:
                delay = policy.get_delay(attempt)
                logger.warning(
                    f"Attempt {attempt + 1} failed: {exc}. Retrying in {delay}s"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"All {policy.max_retries + 1} attempts failed: {exc}")

    if last_error:
        raise last_error
    raise RuntimeError("Unexpected retry state")
