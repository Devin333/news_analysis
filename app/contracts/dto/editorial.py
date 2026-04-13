"""Editorial DTOs for human-in-the-loop operations."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EditorActionType(StrEnum):
    """Editor action types."""

    APPROVE = "approve"
    REJECT = "reject"
    REVISE_COPY = "revise_copy"
    REASSIGN_BOARD = "reassign_board"
    SPLIT_TOPIC = "split_topic"
    MERGE_TOPIC = "merge_topic"
    RERUN_AGENT = "rerun_agent"
    PIN = "pin"
    UNPIN = "unpin"
    FEATURE = "feature"
    ARCHIVE = "archive"
    RESTORE = "restore"


class EditorActionStatus(StrEnum):
    """Editor action status."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERTED = "reverted"


class TargetType(StrEnum):
    """Target types for editor actions."""

    TOPIC = "topic"
    COPY = "copy"
    REPORT = "report"
    ITEM = "item"
    INSIGHT = "insight"


class AgentType(StrEnum):
    """Agent types for rerun requests."""

    HISTORIAN = "historian"
    ANALYST = "analyst"
    WRITER = "writer"
    REVIEWER = "reviewer"


class EditorActionDTO(BaseModel):
    """DTO for editor action."""

    id: int
    target_type: TargetType
    target_id: int
    action_type: EditorActionType
    action_payload: dict[str, Any] = Field(default_factory=dict)
    editor_key: str
    reason: str | None = None
    notes: str | None = None
    status: EditorActionStatus
    error_message: str | None = None
    parent_action_id: int | None = None
    created_at: datetime


class EditorActionCreateDTO(BaseModel):
    """DTO for creating an editor action."""

    target_type: TargetType
    target_id: int
    action_type: EditorActionType
    action_payload: dict[str, Any] = Field(default_factory=dict)
    editor_key: str
    reason: str | None = None
    notes: str | None = None


class ApproveActionDTO(BaseModel):
    """DTO for approve action."""

    target_type: TargetType
    target_id: int
    editor_key: str
    reason: str | None = None
    notes: str | None = None


class RejectActionDTO(BaseModel):
    """DTO for reject action."""

    target_type: TargetType
    target_id: int
    editor_key: str
    reason: str
    notes: str | None = None
    suggest_revision: bool = False


class ReviseCopyDTO(BaseModel):
    """DTO for revise copy action."""

    copy_id: int
    editor_key: str
    new_title: str | None = None
    new_summary: str | None = None
    new_body: str | None = None
    reason: str | None = None


class ReassignBoardDTO(BaseModel):
    """DTO for reassign board action."""

    topic_id: int
    editor_key: str
    new_board_type: str
    reason: str | None = None


class SplitTopicDTO(BaseModel):
    """DTO for split topic action."""

    topic_id: int
    editor_key: str
    split_item_ids: list[int]
    new_topic_title: str | None = None
    reason: str | None = None


class MergeTopicsDTO(BaseModel):
    """DTO for merge topics action."""

    source_topic_ids: list[int]
    target_topic_id: int
    editor_key: str
    reason: str | None = None


class RerunAgentDTO(BaseModel):
    """DTO for rerun agent action."""

    target_type: TargetType
    target_id: int
    agent_type: AgentType
    editor_key: str
    reason: str | None = None
    force: bool = False


class PinContentDTO(BaseModel):
    """DTO for pin/unpin content."""

    target_type: TargetType
    target_id: int
    editor_key: str
    pin_position: int | None = None
    pin_until: datetime | None = None
    reason: str | None = None


class FeatureContentDTO(BaseModel):
    """DTO for feature content."""

    target_type: TargetType
    target_id: int
    editor_key: str
    feature_section: str | None = None
    feature_until: datetime | None = None
    reason: str | None = None


class ArchiveContentDTO(BaseModel):
    """DTO for archive/restore content."""

    target_type: TargetType
    target_id: int
    editor_key: str
    reason: str | None = None


class EditorActionResultDTO(BaseModel):
    """Result of an editor action."""

    action_id: int
    success: bool
    message: str
    affected_ids: list[int] = Field(default_factory=list)
    changes: dict[str, Any] = Field(default_factory=dict)


class EditorActionListDTO(BaseModel):
    """List of editor actions."""

    actions: list[EditorActionDTO]
    total: int
    filters: dict[str, Any] = Field(default_factory=dict)


class EditorActionHistoryDTO(BaseModel):
    """History of actions for a target."""

    target_type: TargetType
    target_id: int
    actions: list[EditorActionDTO]
    total: int
