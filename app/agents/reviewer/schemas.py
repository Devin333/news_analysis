"""Reviewer Agent output schemas.

Defines the structured output formats for the Reviewer Agent,
which reviews and validates generated content.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ReviewStatus(StrEnum):
    """Review status."""

    APPROVE = "approve"
    REVISE = "revise"
    REJECT = "reject"


class IssueType(StrEnum):
    """Type of issue found during review."""

    FACTUAL_DRIFT = "factual_drift"
    UNSUPPORTED_STATEMENT = "unsupported_statement"
    HISTORICAL_MISMATCH = "historical_mismatch"
    VAGUE_SUMMARY = "vague_summary"
    LOW_INFORMATION_DENSITY = "low_information_density"
    REPETITIVE_WORDING = "repetitive_wording"
    MISSING_KEY_POINT = "missing_key_point"
    STYLE_ISSUE = "style_issue"
    CONTRADICTS_ANALYST = "contradicts_analyst"
    CONTRADICTS_HISTORIAN = "contradicts_historian"
    TONE_INAPPROPRIATE = "tone_inappropriate"
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"


class IssueSeverity(StrEnum):
    """Severity of an issue."""

    CRITICAL = "critical"  # Must fix, blocks publication
    MAJOR = "major"  # Should fix
    MINOR = "minor"  # Nice to fix
    SUGGESTION = "suggestion"  # Optional improvement


class ReviewIssue(BaseModel):
    """A single issue found during review."""

    issue_type: IssueType = Field(
        description="Type of issue"
    )
    severity: IssueSeverity = Field(
        description="Severity of the issue"
    )
    description: str = Field(
        description="Description of the issue"
    )
    location: str | None = Field(
        default=None,
        description="Where in the copy the issue was found"
    )
    suggestion: str | None = Field(
        default=None,
        description="Suggested fix"
    )
    evidence: str | None = Field(
        default=None,
        description="Evidence supporting this issue"
    )


class ReviewerOutput(BaseModel):
    """Output schema for Reviewer Agent.

    Contains the review result and any issues found.
    """

    # Overall status
    review_status: ReviewStatus = Field(
        description="Overall review status: approve, revise, or reject"
    )

    # Issues found
    issues: list[ReviewIssue] = Field(
        default_factory=list,
        description="List of issues found"
    )

    # Missing points
    missing_points: list[str] = Field(
        default_factory=list,
        description="Important points that should be included but are missing"
    )

    # Unsupported claims
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="Claims made without supporting evidence"
    )

    # Style issues
    style_issues: list[str] = Field(
        default_factory=list,
        description="Style and tone issues"
    )

    # Revision hints
    revision_hints: list[str] = Field(
        default_factory=list,
        description="Specific hints for revision"
    )

    # Summary
    review_summary: str = Field(
        description="Brief summary of the review"
    )

    # Confidence
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence in the review (0-1)"
    )

    # Metadata
    reviewed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the review was performed"
    )
    reviewer_version: str = Field(
        default="v1",
        description="Version of the reviewer"
    )

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are critical issues."""
        return any(i.severity == IssueSeverity.CRITICAL for i in self.issues)

    @property
    def has_major_issues(self) -> bool:
        """Check if there are major issues."""
        return any(i.severity == IssueSeverity.MAJOR for i in self.issues)

    @property
    def issue_count(self) -> int:
        """Get total issue count."""
        return len(self.issues)

    @property
    def critical_count(self) -> int:
        """Get critical issue count."""
        return sum(1 for i in self.issues if i.severity == IssueSeverity.CRITICAL)

    @property
    def major_count(self) -> int:
        """Get major issue count."""
        return sum(1 for i in self.issues if i.severity == IssueSeverity.MAJOR)


class ReviewerInput(BaseModel):
    """Input schema for Reviewer Agent."""

    # Target
    copy_id: int | None = None
    topic_id: int
    copy_type: str

    # The copy to review
    copy_title: str | None = None
    copy_body: dict[str, Any] = Field(default_factory=dict)

    # Source materials for verification
    topic_title: str
    topic_summary: str | None = None

    # Historian output for fact-checking
    historian_output: dict[str, Any] | None = None
    history_summary: str | None = None
    first_seen_at: datetime | None = None
    what_is_new_this_time: str | None = None
    historical_status: str | None = None

    # Analyst output for judgement verification
    analyst_output: dict[str, Any] | None = None
    why_it_matters: str | None = None
    system_judgement: str | None = None
    likely_audience: list[str] = Field(default_factory=list)
    follow_up_points: list[str] = Field(default_factory=list)

    # Representative items for evidence
    representative_items: list[dict[str, Any]] = Field(default_factory=list)

    # Timeline for verification
    timeline_points: list[dict[str, Any]] = Field(default_factory=list)

    # Key evidence
    key_evidence: list[str] = Field(default_factory=list)

    # Review focus
    focus_areas: list[str] = Field(
        default_factory=list,
        description="Specific areas to focus review on"
    )
