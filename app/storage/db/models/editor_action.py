"""Editor action model for human-in-the-loop operations."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.models_base import Base, JSONType


class EditorAction(Base):
    """Model for recording editor/human actions.

    Supports action types:
    - approve: Approve content
    - reject: Reject content
    - revise_copy: Revise copy text
    - reassign_board: Change topic board
    - split_topic: Split topic into multiple
    - merge_topic: Merge topics
    - rerun_agent: Request agent rerun
    - pin: Pin content
    - unpin: Unpin content
    - feature: Feature content
    - archive: Archive content
    - restore: Restore archived content
    """

    __tablename__ = "editor_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Target information
    target_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of target (topic, copy, report, item)",
    )
    target_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="ID of the target",
    )

    # Action information
    action_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of action performed",
    )
    action_payload_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
        comment="Action-specific payload data",
    )

    # Editor information
    editor_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Editor identifier (user key or system)",
    )

    # Context
    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Reason for the action",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Additional notes",
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="completed",
        comment="Action status (pending, completed, failed, reverted)",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if action failed",
    )

    # Related action (for revert tracking)
    parent_action_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="Parent action ID if this is a revert",
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
            f"<EditorAction(id={self.id}, "
            f"target={self.target_type}:{self.target_id}, "
            f"action={self.action_type}, "
            f"editor={self.editor_key})>"
        )

    @property
    def is_completed(self) -> bool:
        """Check if action is completed."""
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        """Check if action failed."""
        return self.status == "failed"

    @property
    def is_reverted(self) -> bool:
        """Check if action was reverted."""
        return self.status == "reverted"
