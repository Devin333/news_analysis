"""Source related DTOs."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import SourceType


class SourceConfigDTO(BaseModel):
    """Source specific config payload."""

    model_config = ConfigDict(extra="allow")


class SourceCreate(BaseModel):
    """DTO for creating a source."""

    name: str = Field(min_length=1, max_length=255)
    source_type: SourceType
    base_url: str | None = None
    feed_url: str | None = None
    priority: int = Field(default=100, ge=0, le=1000)
    trust_score: float = Field(default=0.5, ge=0.0, le=1.0)
    fetch_interval_minutes: int = Field(default=60, ge=1)
    is_active: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SourceUpdate(BaseModel):
    """DTO for updating source fields."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    base_url: str | None = None
    feed_url: str | None = None
    priority: int | None = Field(default=None, ge=0, le=1000)
    trust_score: float | None = Field(default=None, ge=0.0, le=1.0)
    fetch_interval_minutes: int | None = Field(default=None, ge=1)
    is_active: bool | None = None
    metadata_json: dict[str, Any] | None = None


class SourceRead(BaseModel):
    """DTO for reading source details."""

    id: int
    name: str
    source_type: SourceType
    base_url: str | None
    feed_url: str | None
    priority: int
    trust_score: float
    fetch_interval_minutes: int
    is_active: bool
    metadata_json: dict[str, Any]


# ---------------------------------------------------------------------------
# Collector related DTOs
# ---------------------------------------------------------------------------


class CollectRequest(BaseModel):
    """Request payload sent to a collector for execution."""

    source_id: int
    source_type: SourceType
    base_url: str | None = None
    feed_url: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    max_items: int = Field(default=100, ge=1, le=10000)


class RawCollectedItem(BaseModel):
    """A single raw item produced by a collector."""

    external_id: str | None = None
    url: str | None = None
    canonical_url: str | None = None
    title: str | None = None
    raw_html: str | None = None
    raw_json: dict[str, Any] | None = None
    raw_text: str | None = None
    published_at: datetime | None = None
    author: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class CollectResult(BaseModel):
    """Result returned by a collector after execution."""

    source_id: int
    success: bool = True
    items: list[RawCollectedItem] = Field(default_factory=list)
    error: str | None = None
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
