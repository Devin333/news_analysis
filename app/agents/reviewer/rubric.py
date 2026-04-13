"""Reviewer rubric definitions.

Defines the review criteria and rubrics for different copy types.
"""

from dataclasses import dataclass, field
from typing import Any

from app.agents.reviewer.schemas import IssueSeverity, IssueType


@dataclass
class RubricItem:
    """A single rubric item."""

    name: str
    description: str
    issue_type: IssueType
    default_severity: IssueSeverity
    check_function: str | None = None  # Name of check function
    applies_to: list[str] = field(default_factory=list)  # Copy types


# Core rubric items
CORE_RUBRIC: list[RubricItem] = [
    RubricItem(
        name="Factual Accuracy",
        description="Content must not contradict established facts from source materials",
        issue_type=IssueType.FACTUAL_DRIFT,
        default_severity=IssueSeverity.CRITICAL,
        applies_to=["feed_card", "topic_intro", "trend_card", "report_section"],
    ),
    RubricItem(
        name="Historian Consistency",
        description="Content must not contradict Historian's historical analysis",
        issue_type=IssueType.CONTRADICTS_HISTORIAN,
        default_severity=IssueSeverity.CRITICAL,
        applies_to=["feed_card", "topic_intro", "trend_card", "report_section"],
    ),
    RubricItem(
        name="Analyst Consistency",
        description="Content must not contradict Analyst's judgements",
        issue_type=IssueType.CONTRADICTS_ANALYST,
        default_severity=IssueSeverity.CRITICAL,
        applies_to=["feed_card", "topic_intro", "trend_card", "report_section"],
    ),
    RubricItem(
        name="Supported Claims",
        description="All claims must be supported by evidence from source materials",
        issue_type=IssueType.UNSUPPORTED_STATEMENT,
        default_severity=IssueSeverity.MAJOR,
        applies_to=["feed_card", "topic_intro", "trend_card", "report_section"],
    ),
    RubricItem(
        name="Historical Accuracy",
        description="Historical dates and events must match timeline",
        issue_type=IssueType.HISTORICAL_MISMATCH,
        default_severity=IssueSeverity.CRITICAL,
        applies_to=["topic_intro", "trend_card", "report_section"],
    ),
    RubricItem(
        name="Information Density",
        description="Content should be information-rich, not vague or generic",
        issue_type=IssueType.LOW_INFORMATION_DENSITY,
        default_severity=IssueSeverity.MAJOR,
        applies_to=["feed_card", "topic_intro", "trend_card", "report_section"],
    ),
    RubricItem(
        name="Specificity",
        description="Avoid vague summaries; be specific and concrete",
        issue_type=IssueType.VAGUE_SUMMARY,
        default_severity=IssueSeverity.MAJOR,
        applies_to=["feed_card", "topic_intro", "trend_card", "report_section"],
    ),
    RubricItem(
        name="No Repetition",
        description="Avoid repetitive wording or redundant statements",
        issue_type=IssueType.REPETITIVE_WORDING,
        default_severity=IssueSeverity.MINOR,
        applies_to=["topic_intro", "report_section"],
    ),
    RubricItem(
        name="Key Points Coverage",
        description="Must cover the most important points from source materials",
        issue_type=IssueType.MISSING_KEY_POINT,
        default_severity=IssueSeverity.MAJOR,
        applies_to=["topic_intro", "report_section"],
    ),
    RubricItem(
        name="Appropriate Tone",
        description="Tone should be professional and appropriate for the audience",
        issue_type=IssueType.TONE_INAPPROPRIATE,
        default_severity=IssueSeverity.MINOR,
        applies_to=["feed_card", "topic_intro", "trend_card", "report_section"],
    ),
    RubricItem(
        name="Length Appropriateness",
        description="Content should be neither too short nor too long",
        issue_type=IssueType.TOO_SHORT,
        default_severity=IssueSeverity.MINOR,
        applies_to=["feed_card", "topic_intro", "trend_card", "report_section"],
    ),
]


# Copy type specific requirements
COPY_TYPE_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "feed_card": {
        "required_fields": ["title", "short_summary"],
        "max_title_length": 100,
        "max_summary_length": 200,
        "min_summary_length": 50,
    },
    "topic_intro": {
        "required_fields": ["headline", "intro", "key_takeaways", "why_it_matters"],
        "max_headline_length": 120,
        "min_key_takeaways": 3,
        "max_key_takeaways": 7,
    },
    "trend_card": {
        "required_fields": ["trend_title", "trend_summary", "signal_summary", "stage_label"],
        "max_title_length": 100,
        "required_stage_labels": ["🚀 Emerging", "📈 Growing", "🔥 Hot", "➡️ Steady", "📉 Cooling"],
    },
    "report_section": {
        "required_fields": ["section_title", "section_intro", "key_points"],
        "min_key_points": 3,
        "max_key_points": 7,
    },
}


class ReviewRubric:
    """Review rubric for a specific copy type."""

    def __init__(self, copy_type: str) -> None:
        """Initialize the rubric.

        Args:
            copy_type: Type of copy to review.
        """
        self.copy_type = copy_type
        self.items = [
            item for item in CORE_RUBRIC
            if not item.applies_to or copy_type in item.applies_to
        ]
        self.requirements = COPY_TYPE_REQUIREMENTS.get(copy_type, {})

    def get_required_fields(self) -> list[str]:
        """Get required fields for this copy type."""
        return self.requirements.get("required_fields", [])

    def get_max_length(self, field: str) -> int | None:
        """Get max length for a field."""
        return self.requirements.get(f"max_{field}_length")

    def get_min_length(self, field: str) -> int | None:
        """Get min length for a field."""
        return self.requirements.get(f"min_{field}_length")

    def get_rubric_items(self) -> list[RubricItem]:
        """Get all rubric items for this copy type."""
        return self.items

    def get_critical_items(self) -> list[RubricItem]:
        """Get critical rubric items."""
        return [i for i in self.items if i.default_severity == IssueSeverity.CRITICAL]

    def get_major_items(self) -> list[RubricItem]:
        """Get major rubric items."""
        return [i for i in self.items if i.default_severity == IssueSeverity.MAJOR]

    def to_prompt_text(self) -> str:
        """Convert rubric to prompt text."""
        lines = [f"Review Rubric for {self.copy_type}:", ""]

        # Required fields
        required = self.get_required_fields()
        if required:
            lines.append(f"Required fields: {', '.join(required)}")
            lines.append("")

        # Critical checks
        critical = self.get_critical_items()
        if critical:
            lines.append("CRITICAL (must pass):")
            for item in critical:
                lines.append(f"  - {item.name}: {item.description}")
            lines.append("")

        # Major checks
        major = self.get_major_items()
        if major:
            lines.append("MAJOR (should pass):")
            for item in major:
                lines.append(f"  - {item.name}: {item.description}")
            lines.append("")

        return "\n".join(lines)


def get_rubric(copy_type: str) -> ReviewRubric:
    """Get review rubric for a copy type.

    Args:
        copy_type: Type of copy.

    Returns:
        ReviewRubric for the copy type.
    """
    return ReviewRubric(copy_type)
