"""Subscription DTOs."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SubscriptionType(StrEnum):
    """Subscription type."""

    QUERY = "query"
    TAG = "tag"
    ENTITY = "entity"
    TOPIC = "topic"
    BOARD = "board"


class SubscriptionStatus(StrEnum):
    """Subscription status."""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class NotifyFrequency(StrEnum):
    """Notification frequency."""

    IMMEDIATE = "immediate"
    DAILY = "daily"
    WEEKLY = "weekly"


class MatchMode(StrEnum):
    """Match mode for subscriptions."""

    ANY = "any"
    ALL = "all"
    EXACT = "exact"


class SubscriptionCreateDTO(BaseModel):
    """DTO for creating a subscription."""

    subscription_type: SubscriptionType
    user_key: str

    # Optional fields based on type
    query: str | None = None
    tags: list[str] = Field(default_factory=list)
    board_type: str | None = None
    entity_id: int | None = None
    topic_id: int | None = None

    # Settings
    name: str | None = None
    notify_email: bool = True
    notify_frequency: NotifyFrequency = NotifyFrequency.DAILY
    min_score: float = Field(default=0.5, ge=0.0, le=1.0)
    match_mode: MatchMode = MatchMode.ANY

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)


class SubscriptionReadDTO(BaseModel):
    """DTO for reading a subscription."""

    id: int
    subscription_type: SubscriptionType
    user_key: str

    query: str | None = None
    tags: list[str] = Field(default_factory=list)
    board_type: str | None = None
    entity_id: int | None = None
    topic_id: int | None = None

    name: str | None = None
    status: SubscriptionStatus
    notify_email: bool
    notify_frequency: NotifyFrequency
    min_score: float
    match_mode: MatchMode

    created_at: datetime
    updated_at: datetime
    last_matched_at: datetime | None = None

    # Stats
    match_count: int = 0
    unread_count: int = 0


class SubscriptionUpdateDTO(BaseModel):
    """DTO for updating a subscription."""

    name: str | None = None
    status: SubscriptionStatus | None = None
    notify_email: bool | None = None
    notify_frequency: NotifyFrequency | None = None
    min_score: float | None = None
    match_mode: MatchMode | None = None

    # Update query/tags
    query: str | None = None
    tags: list[str] | None = None


class SubscriptionMatchDTO(BaseModel):
    """DTO for a subscription match event."""

    id: int
    subscription_id: int

    target_type: str
    target_id: int
    target_title: str | None = None
    target_summary: str | None = None

    match_score: float
    match_reason: str | None = None
    matched_fields: list[str] = Field(default_factory=list)
    matched_tags: list[str] = Field(default_factory=list)

    notification_status: str
    is_read: bool
    created_at: datetime


class SubscriptionMatchResultDTO(BaseModel):
    """Result of matching content against subscriptions."""

    content_type: str
    content_id: int
    matched_subscriptions: list[int] = Field(default_factory=list)
    match_details: list[dict[str, Any]] = Field(default_factory=list)
    total_matches: int = 0
