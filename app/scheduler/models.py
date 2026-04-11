"""Scheduler data models."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class JobConfig:
    """Configuration for a scheduled job."""

    job_id: str
    name: str
    cron_expression: str | None = None
    interval_seconds: int | None = None
    max_retries: int = 3
    retry_delay_seconds: int = 60
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class JobRunResult:
    """Result of a single job execution."""

    job_id: str
    success: bool
    message: str = ""
    items_processed: int = 0
    error: str | None = None
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetryPolicy:
    """Retry policy for failed jobs."""

    max_retries: int = 3
    base_delay_seconds: int = 60
    max_delay_seconds: int = 3600
    backoff_multiplier: float = 2.0

    def get_delay(self, attempt: int) -> int:
        """Calculate delay for given attempt number."""
        delay = int(self.base_delay_seconds * (self.backoff_multiplier ** attempt))
        return min(delay, self.max_delay_seconds)
