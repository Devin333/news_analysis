"""Retry policy for agent execution.

This module defines retry strategies for failed operations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from app.bootstrap.logging import get_logger

if TYPE_CHECKING:
    from app.agent_runtime.state import AgentState

logger = get_logger(__name__)


class RetryAction(StrEnum):
    """Actions to take on failure."""

    RETRY = "retry"  # Retry the operation
    SKIP = "skip"  # Skip and continue
    ABORT = "abort"  # Abort execution
    FALLBACK = "fallback"  # Use fallback strategy


@dataclass
class RetryDecision:
    """Decision on how to handle a failure."""

    action: RetryAction
    delay_seconds: float = 0.0
    modified_input: dict[str, Any] | None = None
    message: str = ""
    attempt_number: int = 0
    max_attempts: int = 3


class RetryPolicy(ABC):
    """Abstract base class for retry policies."""

    @abstractmethod
    def should_retry(
        self,
        error: Exception,
        attempt: int,
        state: "AgentState | None" = None,
    ) -> RetryDecision:
        """Determine if and how to retry after an error.

        Args:
            error: The exception that occurred.
            attempt: Current attempt number (1-based).
            state: Optional agent state for context.

        Returns:
            RetryDecision indicating what to do.
        """
        pass


@dataclass
class RetryConfig:
    """Configuration for retry policy."""

    # Maximum retry attempts
    max_attempts: int = 3

    # Base delay between retries (seconds)
    base_delay: float = 1.0

    # Exponential backoff multiplier
    backoff_multiplier: float = 2.0

    # Maximum delay (seconds)
    max_delay: float = 30.0

    # Errors that should not be retried
    non_retryable_errors: list[str] = None

    def __post_init__(self):
        if self.non_retryable_errors is None:
            self.non_retryable_errors = [
                "AuthenticationError",
                "PermissionError",
                "InvalidRequestError",
            ]


class DefaultRetryPolicy(RetryPolicy):
    """Default retry policy with exponential backoff.

    Retries transient errors with increasing delays.
    """

    def __init__(self, config: RetryConfig | None = None) -> None:
        """Initialize the policy.

        Args:
            config: Retry configuration.
        """
        self._config = config or RetryConfig()

    def should_retry(
        self,
        error: Exception,
        attempt: int,
        state: "AgentState | None" = None,
    ) -> RetryDecision:
        """Determine if and how to retry."""
        error_type = type(error).__name__

        # Check if error is non-retryable
        if error_type in self._config.non_retryable_errors:
            logger.warning(f"Non-retryable error: {error_type}")
            return RetryDecision(
                action=RetryAction.ABORT,
                message=f"Non-retryable error: {error_type}",
                attempt_number=attempt,
                max_attempts=self._config.max_attempts,
            )

        # Check if max attempts exceeded
        if attempt >= self._config.max_attempts:
            logger.warning(f"Max retry attempts ({self._config.max_attempts}) exceeded")
            return RetryDecision(
                action=RetryAction.ABORT,
                message=f"Max attempts ({self._config.max_attempts}) exceeded",
                attempt_number=attempt,
                max_attempts=self._config.max_attempts,
            )

        # Calculate delay with exponential backoff
        delay = min(
            self._config.base_delay * (self._config.backoff_multiplier ** (attempt - 1)),
            self._config.max_delay,
        )

        logger.info(f"Retrying after {delay:.1f}s (attempt {attempt + 1}/{self._config.max_attempts})")

        return RetryDecision(
            action=RetryAction.RETRY,
            delay_seconds=delay,
            message=f"Retrying after {delay:.1f}s",
            attempt_number=attempt,
            max_attempts=self._config.max_attempts,
        )

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number.

        Args:
            attempt: Attempt number (1-based).

        Returns:
            Delay in seconds.
        """
        return min(
            self._config.base_delay * (self._config.backoff_multiplier ** (attempt - 1)),
            self._config.max_delay,
        )


class NoRetryPolicy(RetryPolicy):
    """Policy that never retries."""

    def should_retry(
        self,
        error: Exception,
        attempt: int,
        state: "AgentState | None" = None,
    ) -> RetryDecision:
        """Always abort on error."""
        return RetryDecision(
            action=RetryAction.ABORT,
            message="No retry policy - aborting",
            attempt_number=attempt,
            max_attempts=1,
        )


class SkipOnErrorPolicy(RetryPolicy):
    """Policy that skips failed operations and continues."""

    def should_retry(
        self,
        error: Exception,
        attempt: int,
        state: "AgentState | None" = None,
    ) -> RetryDecision:
        """Always skip on error."""
        return RetryDecision(
            action=RetryAction.SKIP,
            message=f"Skipping due to error: {error}",
            attempt_number=attempt,
            max_attempts=1,
        )
