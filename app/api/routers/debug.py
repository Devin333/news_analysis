"""Debug API router for testing and debugging processing pipeline."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.bootstrap.logging import get_logger
from app.common.enums import ContentType
from app.contracts.dto.raw_item import RawItemDTO
from app.processing.pipeline import ProcessingPipeline, process_single_item

logger = get_logger(__name__)

router = APIRouter(prefix="/debug", tags=["debug"])


class ParseRequest(BaseModel):
    """Request to parse raw content."""

    raw_html: str | None = None
    raw_text: str | None = None
    raw_json: dict[str, Any] | None = None
    url: str | None = None
    content_type: ContentType = ContentType.ARTICLE


class ParseResponse(BaseModel):
    """Response from parsing."""

    success: bool
    title: str = ""
    clean_text: str = ""
    excerpt: str | None = None
    author: str | None = None
    language: str | None = None
    word_count: int = 0
    quality_score: float = 0.0
    board_type: str = ""
    tags: list[str] = Field(default_factory=list)
    error: str | None = None


@router.post("/parse", response_model=ParseResponse)
async def debug_parse(request: ParseRequest) -> ParseResponse:
    """Parse raw content and return structured result.

    This endpoint is for debugging and testing the parsing pipeline.
    """
    logger.info("Debug parse request received")

    if not request.raw_html and not request.raw_text and not request.raw_json:
        raise HTTPException(
            status_code=400,
            detail="At least one of raw_html, raw_text, or raw_json is required",
        )

    raw_item = RawItemDTO(
        id=0,
        source_id=0,
        url=request.url,
        canonical_url=request.url,
        raw_html=request.raw_html,
        raw_text=request.raw_text,
        raw_json=request.raw_json,
    )

    normalized, parse_result = process_single_item(
        raw_item, content_type=request.content_type
    )

    if not parse_result.success or normalized is None:
        return ParseResponse(
            success=False,
            error=parse_result.error or "Parsing failed",
        )

    return ParseResponse(
        success=True,
        title=normalized.title,
        clean_text=normalized.clean_text[:1000],  # Truncate for response
        excerpt=normalized.excerpt,
        author=normalized.author,
        language=normalized.language,
        word_count=normalized.metadata_json.get("word_count", 0),
        quality_score=normalized.quality_score,
        board_type=normalized.board_type_candidate.value,
        tags=normalized.metadata_json.get("tags", []),
    )


class PipelineStatsResponse(BaseModel):
    """Pipeline statistics response."""

    parsers_registered: list[str]
    supported_content_types: list[str]


@router.get("/pipeline/stats", response_model=PipelineStatsResponse)
async def get_pipeline_stats() -> PipelineStatsResponse:
    """Get pipeline statistics and configuration."""
    pipeline = ProcessingPipeline()
    parsers = pipeline._parser_registry.list_parsers()
    types = pipeline._parser_registry.list_types()

    return PipelineStatsResponse(
        parsers_registered=[p.name for p in parsers],
        supported_content_types=[t.value for t in types],
    )
