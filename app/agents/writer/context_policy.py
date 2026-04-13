"""Writer context policy.

Controls the context scope and trimming rules for different copy types.
"""

from dataclasses import dataclass
from typing import Any

from app.agents.writer.schemas import CopyType
from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ContextLimits:
    """Limits for context inclusion."""

    max_representative_items: int = 3
    max_timeline_points: int = 5
    max_tags: int = 5
    max_follow_up_points: int = 3
    max_audience_items: int = 3
    include_full_historian: bool = True
    include_full_analyst: bool = True
    include_timeline: bool = True
    include_evidence: bool = False
    summary_max_length: int = 500
    history_summary_max_length: int = 300


# Default limits per copy type
COPY_TYPE_LIMITS: dict[CopyType, ContextLimits] = {
    CopyType.FEED_CARD: ContextLimits(
        max_representative_items=2,
        max_timeline_points=0,
        max_tags=4,
        max_follow_up_points=0,
        max_audience_items=2,
        include_full_historian=False,
        include_full_analyst=False,
        include_timeline=False,
        include_evidence=False,
        summary_max_length=200,
        history_summary_max_length=100,
    ),
    CopyType.TOPIC_INTRO: ContextLimits(
        max_representative_items=5,
        max_timeline_points=10,
        max_tags=10,
        max_follow_up_points=5,
        max_audience_items=5,
        include_full_historian=True,
        include_full_analyst=True,
        include_timeline=True,
        include_evidence=True,
        summary_max_length=1000,
        history_summary_max_length=500,
    ),
    CopyType.TREND_CARD: ContextLimits(
        max_representative_items=3,
        max_timeline_points=3,
        max_tags=5,
        max_follow_up_points=3,
        max_audience_items=3,
        include_full_historian=True,
        include_full_analyst=True,
        include_timeline=True,
        include_evidence=False,
        summary_max_length=300,
        history_summary_max_length=200,
    ),
    CopyType.REPORT_SECTION: ContextLimits(
        max_representative_items=2,  # Per topic
        max_timeline_points=3,  # Per topic
        max_tags=5,
        max_follow_up_points=3,
        max_audience_items=3,
        include_full_historian=True,
        include_full_analyst=True,
        include_timeline=True,
        include_evidence=True,
        summary_max_length=400,
        history_summary_max_length=200,
    ),
}


class WriterContextPolicy:
    """Policy for controlling Writer context.

    Applies limits and trimming based on copy type.
    """

    def __init__(self, copy_type: CopyType) -> None:
        """Initialize the policy.

        Args:
            copy_type: Type of copy being generated.
        """
        self.copy_type = copy_type
        self.limits = COPY_TYPE_LIMITS.get(copy_type, ContextLimits())

    def apply_limits(self, context: dict[str, Any]) -> dict[str, Any]:
        """Apply context limits.

        Args:
            context: Raw context dict.

        Returns:
            Context with limits applied.
        """
        result = context.copy()

        # Trim representative items
        if "representative_items" in result:
            result["representative_items"] = result["representative_items"][
                : self.limits.max_representative_items
            ]

        # Trim timeline
        if "timeline_points" in result:
            if not self.limits.include_timeline:
                result["timeline_points"] = []
            else:
                result["timeline_points"] = result["timeline_points"][
                    : self.limits.max_timeline_points
                ]

        # Trim tags
        if "tags" in result:
            result["tags"] = result["tags"][: self.limits.max_tags]

        # Trim follow-up points
        if "follow_up_points" in result:
            result["follow_up_points"] = result["follow_up_points"][
                : self.limits.max_follow_up_points
            ]

        # Trim audience
        if "likely_audience" in result:
            result["likely_audience"] = result["likely_audience"][
                : self.limits.max_audience_items
            ]

        # Trim summaries
        if "topic_summary" in result and result["topic_summary"]:
            result["topic_summary"] = self._truncate(
                result["topic_summary"], self.limits.summary_max_length
            )

        if "history_summary" in result and result["history_summary"]:
            result["history_summary"] = self._truncate(
                result["history_summary"], self.limits.history_summary_max_length
            )

        # Remove full outputs if not needed
        if not self.limits.include_full_historian:
            result.pop("historian_output", None)

        if not self.limits.include_full_analyst:
            result.pop("analyst_output", None)

        if not self.limits.include_evidence:
            result.pop("evidence_sources", None)
            result.pop("evidence_summary", None)

        return result

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length.

        Args:
            text: Text to truncate.
            max_length: Maximum length.

        Returns:
            Truncated text.
        """
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    def get_prompt_key(self) -> str:
        """Get the prompt key for this copy type.

        Returns:
            Prompt registry key.
        """
        return f"writer_{self.copy_type.value}"

    def should_include_historian(self) -> bool:
        """Check if historian output should be included."""
        return self.limits.include_full_historian

    def should_include_analyst(self) -> bool:
        """Check if analyst output should be included."""
        return self.limits.include_full_analyst

    def should_include_timeline(self) -> bool:
        """Check if timeline should be included."""
        return self.limits.include_timeline


def get_context_policy(copy_type: CopyType) -> WriterContextPolicy:
    """Get context policy for a copy type.

    Args:
        copy_type: Type of copy.

    Returns:
        Configured WriterContextPolicy.
    """
    return WriterContextPolicy(copy_type)
