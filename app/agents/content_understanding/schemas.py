"""Schemas for ContentUnderstandingAgent output."""

from pydantic import BaseModel, Field


class ContentUnderstandingOutput(BaseModel):
    """Output schema for content understanding."""

    content_type_guess: str = Field(
        description="Guessed content type: article, blog, paper, repository, release, discussion"
    )
    board_type_guess: str = Field(
        description="Guessed board type: general, ai, engineering, research"
    )
    key_points: list[str] = Field(
        default_factory=list,
        description="Key points extracted from content"
    )
    importance_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Importance score from 0 to 1"
    )
    candidate_entities: list[str] = Field(
        default_factory=list,
        description="Entities mentioned (companies, products, technologies)"
    )
    why_it_matters_short: str = Field(
        default="",
        description="Brief explanation of why this content matters"
    )
