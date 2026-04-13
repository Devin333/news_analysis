"""Cost monitoring and tracking for LLM and embedding calls."""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Generator

from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


# Model pricing (USD per 1K tokens)
MODEL_PRICING = {
    # OpenAI GPT-4
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    # OpenAI GPT-3.5
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    # Anthropic Claude
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    # Embeddings
    "text-embedding-ada-002": {"input": 0.0001, "output": 0.0},
    "text-embedding-3-small": {"input": 0.00002, "output": 0.0},
    "text-embedding-3-large": {"input": 0.00013, "output": 0.0},
}


@dataclass
class CostRecord:
    """Record of a single API call cost."""

    component: str
    model_name: str
    operation: str
    token_input: int = 0
    token_output: int = 0
    estimated_cost: float = 0.0
    latency_ms: int = 0
    target_type: str | None = None
    target_id: int | None = None
    agent_name: str | None = None
    request_id: str | None = None
    status: str = "success"
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def token_total(self) -> int:
        """Total tokens used."""
        return self.token_input + self.token_output


class CostTracker:
    """Tracker for accumulating costs across operations."""

    def __init__(self) -> None:
        """Initialize the tracker."""
        self._records: list[CostRecord] = []
        self._start_time: datetime | None = None

    def start(self) -> None:
        """Start tracking."""
        self._start_time = datetime.now(timezone.utc)
        self._records = []

    def record(self, record: CostRecord) -> None:
        """Add a cost record.

        Args:
            record: Cost record to add.
        """
        self._records.append(record)

    def get_records(self) -> list[CostRecord]:
        """Get all records."""
        return self._records.copy()

    def get_total_cost(self) -> float:
        """Get total cost."""
        return sum(r.estimated_cost for r in self._records)

    def get_total_tokens(self) -> int:
        """Get total tokens."""
        return sum(r.token_total for r in self._records)

    def get_summary(self) -> dict[str, Any]:
        """Get cost summary.

        Returns:
            Summary dict.
        """
        by_model: dict[str, dict[str, Any]] = {}
        by_component: dict[str, dict[str, Any]] = {}
        by_agent: dict[str, dict[str, Any]] = {}

        for record in self._records:
            # By model
            if record.model_name not in by_model:
                by_model[record.model_name] = {"cost": 0.0, "tokens": 0, "calls": 0}
            by_model[record.model_name]["cost"] += record.estimated_cost
            by_model[record.model_name]["tokens"] += record.token_total
            by_model[record.model_name]["calls"] += 1

            # By component
            if record.component not in by_component:
                by_component[record.component] = {"cost": 0.0, "tokens": 0, "calls": 0}
            by_component[record.component]["cost"] += record.estimated_cost
            by_component[record.component]["tokens"] += record.token_total
            by_component[record.component]["calls"] += 1

            # By agent
            if record.agent_name:
                if record.agent_name not in by_agent:
                    by_agent[record.agent_name] = {"cost": 0.0, "tokens": 0, "calls": 0}
                by_agent[record.agent_name]["cost"] += record.estimated_cost
                by_agent[record.agent_name]["tokens"] += record.token_total
                by_agent[record.agent_name]["calls"] += 1

        return {
            "total_cost": self.get_total_cost(),
            "total_tokens": self.get_total_tokens(),
            "total_calls": len(self._records),
            "by_model": by_model,
            "by_component": by_component,
            "by_agent": by_agent,
            "start_time": self._start_time.isoformat() if self._start_time else None,
        }


def estimate_cost(
    model_name: str,
    input_tokens: int,
    output_tokens: int = 0,
) -> float:
    """Estimate cost for token usage.

    Args:
        model_name: Model name.
        input_tokens: Input tokens.
        output_tokens: Output tokens.

    Returns:
        Estimated cost in USD.
    """
    pricing = MODEL_PRICING.get(model_name)
    if not pricing:
        # Default pricing for unknown models
        pricing = {"input": 0.001, "output": 0.002}

    input_cost = (input_tokens / 1000) * pricing["input"]
    output_cost = (output_tokens / 1000) * pricing["output"]

    return input_cost + output_cost


def create_llm_cost_record(
    model_name: str,
    operation: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    *,
    target_type: str | None = None,
    target_id: int | None = None,
    agent_name: str | None = None,
    request_id: str | None = None,
    status: str = "success",
    error_message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> CostRecord:
    """Create a cost record for LLM call.

    Args:
        model_name: Model name.
        operation: Operation name.
        input_tokens: Input tokens.
        output_tokens: Output tokens.
        latency_ms: Latency in milliseconds.
        target_type: Optional target type.
        target_id: Optional target ID.
        agent_name: Optional agent name.
        request_id: Optional request ID.
        status: Request status.
        error_message: Optional error message.
        metadata: Optional metadata.

    Returns:
        CostRecord.
    """
    return CostRecord(
        component="llm",
        model_name=model_name,
        operation=operation,
        token_input=input_tokens,
        token_output=output_tokens,
        estimated_cost=estimate_cost(model_name, input_tokens, output_tokens),
        latency_ms=latency_ms,
        target_type=target_type,
        target_id=target_id,
        agent_name=agent_name,
        request_id=request_id,
        status=status,
        error_message=error_message,
        metadata=metadata or {},
    )


def create_embedding_cost_record(
    model_name: str,
    operation: str,
    input_tokens: int,
    latency_ms: int,
    *,
    target_type: str | None = None,
    target_id: int | None = None,
    batch_size: int = 1,
    metadata: dict[str, Any] | None = None,
) -> CostRecord:
    """Create a cost record for embedding call.

    Args:
        model_name: Model name.
        operation: Operation name.
        input_tokens: Input tokens.
        latency_ms: Latency in milliseconds.
        target_type: Optional target type.
        target_id: Optional target ID.
        batch_size: Batch size.
        metadata: Optional metadata.

    Returns:
        CostRecord.
    """
    return CostRecord(
        component="embedding",
        model_name=model_name,
        operation=operation,
        token_input=input_tokens,
        token_output=0,
        estimated_cost=estimate_cost(model_name, input_tokens, 0),
        latency_ms=latency_ms,
        target_type=target_type,
        target_id=target_id,
        metadata={"batch_size": batch_size, **(metadata or {})},
    )


@contextmanager
def track_llm_call(
    model_name: str,
    operation: str,
    tracker: CostTracker | None = None,
    **kwargs: Any,
) -> Generator[dict[str, Any], None, None]:
    """Context manager to track LLM call cost.

    Args:
        model_name: Model name.
        operation: Operation name.
        tracker: Optional cost tracker.
        **kwargs: Additional record fields.

    Yields:
        Dict to populate with token counts.
    """
    start_time = time.time()
    result: dict[str, Any] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "request_id": None,
        "status": "success",
        "error_message": None,
    }

    try:
        yield result
    except Exception as e:
        result["status"] = "error"
        result["error_message"] = str(e)
        raise
    finally:
        latency_ms = int((time.time() - start_time) * 1000)

        record = create_llm_cost_record(
            model_name=model_name,
            operation=operation,
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            latency_ms=latency_ms,
            request_id=result.get("request_id"),
            status=result["status"],
            error_message=result.get("error_message"),
            **kwargs,
        )

        if tracker:
            tracker.record(record)

        logger.debug(
            f"LLM call: model={model_name}, op={operation}, "
            f"tokens={record.token_total}, cost=${record.estimated_cost:.6f}, "
            f"latency={latency_ms}ms"
        )


@contextmanager
def track_embedding_call(
    model_name: str,
    operation: str,
    tracker: CostTracker | None = None,
    **kwargs: Any,
) -> Generator[dict[str, Any], None, None]:
    """Context manager to track embedding call cost.

    Args:
        model_name: Model name.
        operation: Operation name.
        tracker: Optional cost tracker.
        **kwargs: Additional record fields.

    Yields:
        Dict to populate with token counts.
    """
    start_time = time.time()
    result: dict[str, Any] = {
        "input_tokens": 0,
        "batch_size": 1,
    }

    try:
        yield result
    finally:
        latency_ms = int((time.time() - start_time) * 1000)

        record = create_embedding_cost_record(
            model_name=model_name,
            operation=operation,
            input_tokens=result["input_tokens"],
            latency_ms=latency_ms,
            batch_size=result.get("batch_size", 1),
            **kwargs,
        )

        if tracker:
            tracker.record(record)

        logger.debug(
            f"Embedding call: model={model_name}, op={operation}, "
            f"tokens={record.token_total}, cost=${record.estimated_cost:.6f}, "
            f"latency={latency_ms}ms"
        )


# Global tracker for convenience
_global_tracker: CostTracker | None = None


def get_global_tracker() -> CostTracker:
    """Get or create global cost tracker."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = CostTracker()
        _global_tracker.start()
    return _global_tracker


def reset_global_tracker() -> None:
    """Reset global cost tracker."""
    global _global_tracker
    _global_tracker = CostTracker()
    _global_tracker.start()
