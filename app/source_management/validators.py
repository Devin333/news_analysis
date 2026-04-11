"""Source validators."""

from app.common.enums import SourceType
from app.common.exceptions import ValidationError
from app.contracts.dto.source import SourceCreate, SourceUpdate


class SourceValidator:
    """Validate source payloads by source type."""

    @staticmethod
    def validate_create(data: SourceCreate) -> None:
        """Validate source creation data."""
        if data.source_type == SourceType.RSS and not data.feed_url:
            raise ValidationError("RSS source requires feed_url")

        if data.source_type == SourceType.WEB and not data.base_url:
            raise ValidationError("Web source requires base_url")

        if data.source_type == SourceType.GITHUB and not data.base_url:
            raise ValidationError("GitHub source requires base_url")

        if data.source_type == SourceType.ARXIV and not data.base_url:
            raise ValidationError("arXiv source requires base_url")

    @staticmethod
    def validate_update(data: SourceUpdate) -> None:
        """Validate update payload consistency."""
        if data.feed_url is not None and not data.feed_url.strip():
            raise ValidationError("feed_url cannot be blank")

        if data.base_url is not None and not data.base_url.strip():
            raise ValidationError("base_url cannot be blank")
