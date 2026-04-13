"""Cost log model for tracking LLM and embedding costs."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.models_base import Base, JSONType


class CostLog(Base):
    """Model for logging LLM and embedding costs.

    Tracks:
    - LLM API calls
    - Embedding API calls
    - Token usage
    - Estimated costs
    - Latency
    """

    __tablename__ = "cost_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Component information
    component: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Component name (llm, embedding, agent)",
    )
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Model name (gpt-4, text-embedding-ada-002, etc.)",
    )

    # Target information (optional)
    target_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Target type (topic, item, report)",
    )
    target_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="Target ID",
    )

    # Operation context
    operation: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Operation name (generate, embed, classify)",
    )
    agent_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Agent name if applicable",
    )

    # Token usage
    token_input: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Input/prompt tokens",
    )
    token_output: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Output/completion tokens",
    )
    token_total: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total tokens",
    )

    # Cost estimation
    estimated_cost: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="Estimated cost in USD",
    )

    # Performance
    latency_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Latency in milliseconds",
    )

    # Request/Response info
    request_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="API request ID",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="success",
        comment="Request status (success, error, timeout)",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if failed",
    )

    # Additional metadata
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
        comment="Additional metadata",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<CostLog(id={self.id}, "
            f"component={self.component}, "
            f"model={self.model_name}, "
            f"tokens={self.token_total}, "
            f"cost=${self.estimated_cost:.6f})>"
        )

    @property
    def cost_per_1k_tokens(self) -> float:
        """Calculate cost per 1000 tokens."""
        if self.token_total == 0:
            return 0.0
        return (self.estimated_cost / self.token_total) * 1000
