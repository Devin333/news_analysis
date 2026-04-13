"""Fact Guard validator.

Validates factual accuracy of content.
"""

from datetime import datetime
from typing import Any

from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


class FactGuardIssue:
    """An issue found by fact guard."""

    def __init__(
        self,
        issue_type: str,
        severity: str,
        description: str,
        field: str | None = None,
    ) -> None:
        self.issue_type = issue_type
        self.severity = severity
        self.description = description
        self.field = field

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_type": self.issue_type,
            "severity": self.severity,
            "description": self.description,
            "field": self.field,
        }


class FactGuard:
    """Validates factual accuracy of content.

    Performs rule-based checks that don't require LLM.
    """

    def validate(
        self,
        copy_body: dict[str, Any],
        *,
        historian_output: dict[str, Any] | None = None,
        analyst_output: dict[str, Any] | None = None,
        timeline_points: list[dict[str, Any]] | None = None,
    ) -> list[FactGuardIssue]:
        """Validate content for factual issues.

        Args:
            copy_body: The copy content.
            historian_output: Historian output for verification.
            analyst_output: Analyst output for verification.
            timeline_points: Timeline for date verification.

        Returns:
            List of issues found.
        """
        issues = []

        # Check first_seen_at validity
        issues.extend(self._check_first_seen_at(copy_body, historian_output))

        # Check timeline order
        issues.extend(self._check_timeline_order(timeline_points))

        # Check metric validity
        issues.extend(self._check_metrics(copy_body))

        # Check date consistency
        issues.extend(self._check_date_consistency(copy_body, historian_output))

        return issues

    def _check_first_seen_at(
        self,
        copy_body: dict[str, Any],
        historian_output: dict[str, Any] | None,
    ) -> list[FactGuardIssue]:
        """Check first_seen_at validity."""
        issues = []

        if historian_output and historian_output.get("first_seen_at"):
            first_seen = historian_output["first_seen_at"]

            # Check if it's in the future
            if isinstance(first_seen, datetime):
                if first_seen > datetime.utcnow():
                    issues.append(FactGuardIssue(
                        issue_type="invalid_date",
                        severity="critical",
                        description="first_seen_at is in the future",
                        field="first_seen_at",
                    ))

            # Check if copy mentions a different date
            # (This would need more sophisticated parsing)

        return issues

    def _check_timeline_order(
        self,
        timeline_points: list[dict[str, Any]] | None,
    ) -> list[FactGuardIssue]:
        """Check timeline is in chronological order."""
        issues = []

        if not timeline_points:
            return issues

        prev_time = None
        for i, point in enumerate(timeline_points):
            event_time = point.get("event_time")
            if event_time and prev_time:
                if isinstance(event_time, datetime) and isinstance(prev_time, datetime):
                    if event_time < prev_time:
                        issues.append(FactGuardIssue(
                            issue_type="timeline_order",
                            severity="major",
                            description=f"Timeline event {i} is out of order",
                            field="timeline",
                        ))
            prev_time = event_time

        return issues

    def _check_metrics(
        self,
        copy_body: dict[str, Any],
    ) -> list[FactGuardIssue]:
        """Check metric validity."""
        issues = []

        # Check for negative counts
        for field in ["item_count", "source_count"]:
            value = copy_body.get(field)
            if value is not None and value < 0:
                issues.append(FactGuardIssue(
                    issue_type="invalid_metric",
                    severity="critical",
                    description=f"{field} cannot be negative",
                    field=field,
                ))

        # Check score ranges
        for field in ["heat_score", "trend_score", "confidence"]:
            value = copy_body.get(field)
            if value is not None:
                if value < 0 or value > 1:
                    issues.append(FactGuardIssue(
                        issue_type="invalid_metric",
                        severity="major",
                        description=f"{field} should be between 0 and 1",
                        field=field,
                    ))

        return issues

    def _check_date_consistency(
        self,
        copy_body: dict[str, Any],
        historian_output: dict[str, Any] | None,
    ) -> list[FactGuardIssue]:
        """Check date consistency."""
        issues = []

        if not historian_output:
            return issues

        first_seen = historian_output.get("first_seen_at")
        last_seen = historian_output.get("last_seen_at")

        if first_seen and last_seen:
            if isinstance(first_seen, datetime) and isinstance(last_seen, datetime):
                if first_seen > last_seen:
                    issues.append(FactGuardIssue(
                        issue_type="date_inconsistency",
                        severity="critical",
                        description="first_seen_at is after last_seen_at",
                        field="dates",
                    ))

        return issues
