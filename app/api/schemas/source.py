"""API schemas for source management."""

from typing import Any

from pydantic import BaseModel, Field

from app.common.enums import SourceType


class SourceCreateRequest(BaseModel):
    """Create source request schema."""

    name: str = Field(min_length=1, max_length=255)
    source_type: SourceType
    base_url: str | None = None
    feed_url: str | None = None
    priority: int = Field(default=100, ge=0, le=1000)
    trust_score: float = Field(default=0.5, ge=0.0, le=1.0)
    fetch_interval_minutes: int = Field(default=60, ge=1)
    is_active: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SourceUpdateRequest(BaseModel):
    """Update source request schema."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    base_url: str | None = None
    feed_url: str | None = None
    priority: int | None = Field(default=None, ge=0, le=1000)
    trust_score: float | None = Field(default=None, ge=0.0, le=1.0)
    fetch_interval_minutes: int | None = Field(default=None, ge=1)
    is_active: bool | None = None
    metadata_json: dict[str, Any] | None = None


class SourceResponse(BaseModel):
    """Source response schema."""

    id: int
    name: str
    source_type: SourceType | str
    base_url: str | None = None
    feed_url: str | None = None
    priority: int
    trust_score: float
    fetch_interval_minutes: int
    is_active: bool
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SourceListResponse(BaseModel):
    """Source list response schema."""

    items: list[SourceResponse]
    total: int
