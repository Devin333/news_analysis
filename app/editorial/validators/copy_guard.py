"""Copy Guard validator.

Validates copy quality and completeness.
"""

from typing import Any

from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


class CopyGuardIssue:
    """An issue found by copy guard."""

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


# Minimum lengths for different fields
MIN_LENGTHS = {
    "title": 10,
    "headline": 10,
    "short_summary": 30,
    "intro": 50,
    "why_it_matters": 30,
    "trend_summary": 30,
    "section_intro": 30,
}

# Maximum lengths for different fields
MAX_LENGTHS = {
    "title": 150,
    "headline": 150,
    "short_summary": 300,
    "why_it_matters_short": 150,
}

# Vague phrases to detect
VAGUE_PHRASES = [
    "important development",
    "significant progress",
    "major advancement",
    "notable achievement",
    "interesting development",
    "various aspects",
    "many things",
    "a lot of",
    "some people",
    "it is said",
    "reportedly",
    "allegedly",
    "in some ways",
    "to some extent",
]


class CopyGuard:
    """Validates copy quality and completeness.

    Performs rule-based checks on copy content.
    """

    def validate(
        self,
        copy_body: dict[str, Any],
        copy_type: str,
    ) -> list[CopyGuardIssue]:
        """Validate copy content.

        Args:
            copy_body: The copy content.
            copy_type: Type of copy.

        Returns:
            List of issues found.
        """
        issues = []

        # Check required fields
        issues.extend(self._check_required_fields(copy_body, copy_type))

        # Check lengths
        issues.extend(self._check_lengths(copy_body))

        # Check for vague language
        issues.extend(self._check_vague_language(copy_body))

        # Check for empty lists
        issues.extend(self._check_empty_lists(copy_body, copy_type))

        # Check for repetition
        issues.extend(self._check_repetition(copy_body))

        return issues

    def _check_required_fields(
        self,
        copy_body: dict[str, Any],
        copy_type: str,
    ) -> list[CopyGuardIssue]:
        """Check required fields are present."""
        issues = []

        required_fields = {
            "feed_card": ["title", "short_summary"],
            "topic_intro": ["headline", "intro", "key_takeaways", "why_it_matters"],
            "trend_card": ["trend_title", "trend_summary", "signal_summary", "stage_label"],
            "report_section": ["section_title", "section_intro", "key_points"],
        }

        fields = required_fields.get(copy_type, [])
        for field in fields:
            value = copy_body.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                issues.append(CopyGuardIssue(
                    issue_type="missing_field",
                    severity="critical",
                    description=f"Required field '{field}' is missing or empty",
                    field=field,
                ))
            elif isinstance(value, list) and len(value) == 0:
                issues.append(CopyGuardIssue(
                    issue_type="empty_list",
                    severity="major",
                    description=f"Required field '{field}' is an empty list",
                    field=field,
                ))

        return issues

    def _check_lengths(
        self,
        copy_body: dict[str, Any],
    ) -> list[CopyGuardIssue]:
        """Check field lengths."""
        issues = []

        for field, min_len in MIN_LENGTHS.items():
            value = copy_body.get(field)
            if value and isinstance(value, str):
                if len(value) < min_len:
                    issues.append(CopyGuardIssue(
                        issue_type="too_short",
                        severity="major",
                        description=f"Field '{field}' is too short (min {min_len} chars)",
                        field=field,
                    ))

        for field, max_len in MAX_LENGTHS.items():
            value = copy_body.get(field)
            if value and isinstance(value, str):
                if len(value) > max_len:
                    issues.append(CopyGuardIssue(
                        issue_type="too_long",
                        severity="minor",
                        description=f"Field '{field}' is too long (max {max_len} chars)",
                        field=field,
                    ))

        return issues

    def _check_vague_language(
        self,
        copy_body: dict[str, Any],
    ) -> list[CopyGuardIssue]:
        """Check for vague language."""
        issues = []

        text_fields = ["title", "headline", "short_summary", "intro", "why_it_matters",
                       "trend_summary", "section_intro"]

        vague_count = 0
        for field in text_fields:
            value = copy_body.get(field)
            if value and isinstance(value, str):
                value_lower = value.lower()
                for phrase in VAGUE_PHRASES:
                    if phrase in value_lower:
                        vague_count += 1
                        if vague_count <= 2:  # Only report first few
                            issues.append(CopyGuardIssue(
                                issue_type="vague_language",
                                severity="minor",
                                description=f"Vague phrase '{phrase}' found in '{field}'",
                                field=field,
                            ))

        if vague_count > 3:
            issues.append(CopyGuardIssue(
                issue_type="high_vagueness",
                severity="major",
                description=f"Content has high vagueness ({vague_count} vague phrases)",
                field=None,
            ))

        return issues

    def _check_empty_lists(
        self,
        copy_body: dict[str, Any],
        copy_type: str,
    ) -> list[CopyGuardIssue]:
        """Check for empty lists that should have content."""
        issues = []

        list_requirements = {
            "topic_intro": {"key_takeaways": 3},
            "report_section": {"key_points": 3},
        }

        requirements = list_requirements.get(copy_type, {})
        for field, min_count in requirements.items():
            value = copy_body.get(field)
            if value and isinstance(value, list):
                if len(value) < min_count:
                    issues.append(CopyGuardIssue(
                        issue_type="insufficient_items",
                        severity="major",
                        description=f"Field '{field}' has fewer than {min_count} items",
                        field=field,
                    ))

        return issues

    def _check_repetition(
        self,
        copy_body: dict[str, Any],
    ) -> list[CopyGuardIssue]:
        """Check for repetitive content."""
        issues = []

        # Check if title/headline is repeated in summary/intro
        title = copy_body.get("title") or copy_body.get("headline") or ""
        summary = copy_body.get("short_summary") or copy_body.get("intro") or ""

        if title and summary:
            title_lower = title.lower().strip()
            summary_lower = summary.lower().strip()

            # Check if title is contained in summary verbatim
            if title_lower in summary_lower:
                issues.append(CopyGuardIssue(
                    issue_type="repetition",
                    severity="minor",
                    description="Title is repeated verbatim in summary/intro",
                    field="title",
                ))

        # Check for repeated phrases in lists
        for field in ["key_takeaways", "key_points", "follow_up_points"]:
            items = copy_body.get(field, [])
            if items and isinstance(items, list):
                seen = set()
                for item in items:
                    if isinstance(item, str):
                        item_lower = item.lower().strip()
                        if item_lower in seen:
                            issues.append(CopyGuardIssue(
                                issue_type="duplicate_item",
                                severity="minor",
                                description=f"Duplicate item in '{field}'",
                                field=field,
                            ))
                        seen.add(item_lower)

        return issues
