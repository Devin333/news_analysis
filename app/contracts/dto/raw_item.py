"""Raw item DTOs."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RawItemDTO(BaseModel):
    """DTO representing a raw collected item."""

    id: int | None = None
    source_id: int
    external_id: str | None = None
    url: str | None = None
    canonical_url: str | None = None
    raw_html: str | None = None
    raw_json: dict[str, Any] | None = None
    raw_text: str | None = None
    fetched_at: datetime | None = None
    checksum: str | None = None
    parse_status: str = Field(default="pending")
