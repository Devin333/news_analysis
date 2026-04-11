"""Parser result DTO for parsed content."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ParseResult(BaseModel):
    """Result of parsing a raw item."""

    success: bool = True
    title: str = ""
    clean_text: str = ""
    excerpt: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    language: str | None = None
    tags: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    word_count: int = 0
    reading_time_minutes: int = 0
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def failure(cls, error: str) -> "ParseResult":
        """Create a failed parse result."""
        return cls(success=False, error=error)
