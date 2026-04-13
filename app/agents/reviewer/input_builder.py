"""Reviewer Agent input builder.

Constructs inputs for the Reviewer Agent with evidence
from source materials.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from app.agents.reviewer.schemas import ReviewerInput
from app.bootstrap.logging import get_logger

if TYPE_CHECKING:
    from app.contracts.dto.topic import TopicReadDTO

logger = get_logger(__name__)


class ReviewerInputBuilder:
    """Builds inputs for the Reviewer Agent.

    Gathers evidence from source materials for review.
    """

    def build_review_input(
        self,
        topic: "TopicReadDTO",
        copy_type: str,
        copy_body: dict[str, Any],
        *,
        copy_id: int | None = None,
        copy_title: str | None = None,
        historian_output: dict[str, Any] | None = None,
        analyst_output: dict[str, Any] | None = None,
        representative_items: list[dict[str, Any]] | None = None,
        timeline_points: list[dict[str, Any]] | None = None,
        focus_areas: list[str] | None = None,
    ) -> ReviewerInput:
        """Build input for review.

        Args:
            topic: Topic data.
            copy_type: Type of copy being reviewed.
            copy_body: The copy content to review.
            copy_id: Optional copy ID.
            copy_title: Optional copy title.
            historian_output: Optional historian output.
            analyst_output: Optional analyst output.
            representative_items: Optional representative items.
            timeline_points: Optional timeline points.
            focus_areas: Optional areas to focus review on.

        Returns:
            ReviewerInput for the review.
        """
        input_data = ReviewerInput(
            copy_id=copy_id,
            topic_id=topic.id,
            copy_type=copy_type,
            copy_title=copy_title,
            copy_body=copy_body,
            topic_title=topic.title,
            topic_summary=topic.summary,
        )

        # Add historian output
        if historian_output:
            input_data.historian_output = historian_output
            input_data.history_summary = historian_output.get("history_summary")
            input_data.first_seen_at = historian_output.get("first_seen_at")
            input_data.what_is_new_this_time = historian_output.get("what_is_new_this_time")
            input_data.historical_status = historian_output.get("historical_status")

        # Add analyst output
        if analyst_output:
            input_data.analyst_output = analyst_output
            input_data.why_it_matters = analyst_output.get("why_it_matters")
            input_data.system_judgement = analyst_output.get("system_judgement")
            input_data.likely_audience = analyst_output.get("likely_audience", [])
            input_data.follow_up_points = analyst_output.get("follow_up_points", [])

        # Add representative items
        if representative_items:
            input_data.representative_items = representative_items[:5]

        # Add timeline
        if timeline_points:
            input_data.timeline_points = timeline_points[:10]

        # Extract key evidence
        input_data.key_evidence = self._extract_key_evidence(
            historian_output=historian_output,
            analyst_output=analyst_output,
            representative_items=representative_items,
        )

        # Add focus areas
        if focus_areas:
            input_data.focus_areas = focus_areas

        return input_data

    def _extract_key_evidence(
        self,
        historian_output: dict[str, Any] | None = None,
        analyst_output: dict[str, Any] | None = None,
        representative_items: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        """Extract key evidence for review.

        Args:
            historian_output: Historian output.
            analyst_output: Analyst output.
            representative_items: Representative items.

        Returns:
            List of key evidence strings.
        """
        evidence = []

        # From historian
        if historian_output:
            if historian_output.get("history_summary"):
                evidence.append(f"History: {historian_output['history_summary']}")
            if historian_output.get("what_is_new_this_time"):
                evidence.append(f"What's new: {historian_output['what_is_new_this_time']}")
            if historian_output.get("first_seen_at"):
                evidence.append(f"First seen: {historian_output['first_seen_at']}")

        # From analyst
        if analyst_output:
            if analyst_output.get("why_it_matters"):
                evidence.append(f"Why it matters: {analyst_output['why_it_matters']}")
            if analyst_output.get("system_judgement"):
                evidence.append(f"Judgement: {analyst_output['system_judgement']}")

        # From items
        if representative_items:
            for item in representative_items[:3]:
                title = item.get("title", "")
                if title:
                    evidence.append(f"Source: {title}")

        return evidence

    def build_prompt_context(self, reviewer_input: ReviewerInput) -> str:
        """Build prompt context string from ReviewerInput.

        Args:
            reviewer_input: The reviewer input.

        Returns:
            Formatted context string for the prompt.
        """
        lines = [
            "=== CONTENT TO REVIEW ===",
            f"Copy Type: {reviewer_input.copy_type}",
        ]

        if reviewer_input.copy_title:
            lines.append(f"Title: {reviewer_input.copy_title}")

        lines.append("")
        lines.append("Copy Body:")
        for key, value in reviewer_input.copy_body.items():
            if isinstance(value, list):
                lines.append(f"  {key}:")
                for item in value[:5]:
                    lines.append(f"    - {item}")
            else:
                lines.append(f"  {key}: {value}")

        lines.append("")
        lines.append("=== SOURCE MATERIALS ===")
        lines.append(f"Topic: {reviewer_input.topic_title}")
        if reviewer_input.topic_summary:
            lines.append(f"Summary: {reviewer_input.topic_summary}")

        # Historian context
        if reviewer_input.historian_output or reviewer_input.history_summary:
            lines.append("")
            lines.append("Historical Context (from Historian):")
            if reviewer_input.historical_status:
                lines.append(f"  Status: {reviewer_input.historical_status}")
            if reviewer_input.first_seen_at:
                lines.append(f"  First Seen: {reviewer_input.first_seen_at}")
            if reviewer_input.history_summary:
                lines.append(f"  History: {reviewer_input.history_summary}")
            if reviewer_input.what_is_new_this_time:
                lines.append(f"  What's New: {reviewer_input.what_is_new_this_time}")

        # Analyst context
        if reviewer_input.analyst_output or reviewer_input.why_it_matters:
            lines.append("")
            lines.append("Analysis (from Analyst):")
            if reviewer_input.why_it_matters:
                lines.append(f"  Why It Matters: {reviewer_input.why_it_matters}")
            if reviewer_input.system_judgement:
                lines.append(f"  Judgement: {reviewer_input.system_judgement}")
            if reviewer_input.likely_audience:
                lines.append(f"  Audience: {', '.join(reviewer_input.likely_audience)}")

        # Key evidence
        if reviewer_input.key_evidence:
            lines.append("")
            lines.append("Key Evidence:")
            for ev in reviewer_input.key_evidence:
                lines.append(f"  - {ev}")

        # Timeline
        if reviewer_input.timeline_points:
            lines.append("")
            lines.append("Timeline:")
            for point in reviewer_input.timeline_points[:5]:
                time = point.get("event_time", "")
                title = point.get("title", "")
                lines.append(f"  - {time}: {title}")

        # Focus areas
        if reviewer_input.focus_areas:
            lines.append("")
            lines.append("Focus Areas:")
            for area in reviewer_input.focus_areas:
                lines.append(f"  - {area}")

        return "\n".join(lines)


class EvidenceSelector:
    """Selects the most important evidence for review."""

    def select_evidence(
        self,
        historian_output: dict[str, Any] | None = None,
        analyst_output: dict[str, Any] | None = None,
        representative_items: list[dict[str, Any]] | None = None,
        timeline_points: list[dict[str, Any]] | None = None,
        *,
        max_items: int = 10,
    ) -> list[dict[str, Any]]:
        """Select the most important evidence.

        Args:
            historian_output: Historian output.
            analyst_output: Analyst output.
            representative_items: Representative items.
            timeline_points: Timeline points.
            max_items: Maximum evidence items.

        Returns:
            List of evidence dicts.
        """
        evidence = []

        # Add historian evidence
        if historian_output:
            evidence.append({
                "type": "historian",
                "importance": 1.0,
                "content": {
                    "history_summary": historian_output.get("history_summary"),
                    "what_is_new": historian_output.get("what_is_new_this_time"),
                    "status": historian_output.get("historical_status"),
                },
            })

        # Add analyst evidence
        if analyst_output:
            evidence.append({
                "type": "analyst",
                "importance": 1.0,
                "content": {
                    "why_it_matters": analyst_output.get("why_it_matters"),
                    "judgement": analyst_output.get("system_judgement"),
                },
            })

        # Add representative items
        if representative_items:
            for i, item in enumerate(representative_items[:3]):
                evidence.append({
                    "type": "item",
                    "importance": 0.8 - (i * 0.1),
                    "content": {
                        "title": item.get("title"),
                        "summary": item.get("summary", "")[:200],
                    },
                })

        # Add timeline milestones
        if timeline_points:
            milestones = [
                p for p in timeline_points
                if p.get("importance_score", 0) >= 0.8
            ][:3]
            for point in milestones:
                evidence.append({
                    "type": "timeline",
                    "importance": 0.7,
                    "content": {
                        "time": point.get("event_time"),
                        "title": point.get("title"),
                    },
                })

        # Sort by importance and limit
        evidence.sort(key=lambda x: x["importance"], reverse=True)
        return evidence[:max_items]
