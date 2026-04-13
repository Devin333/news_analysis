"""Historian output validators.

Provides validation for historian output to catch obvious errors.
"""

from datetime import datetime, timezone
from typing import Any

from app.agents.historian.schemas import HistorianOutput, HistoricalStatus
from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


class HistorianValidator:
    """Validator for historian output."""

    def __init__(self) -> None:
        """Initialize the validator."""
        self._errors: list[str] = []
        self._warnings: list[str] = []

    def validate(self, output: HistorianOutput) -> "ValidationResult":
        """Validate historian output.

        Args:
            output: HistorianOutput to validate.

        Returns:
            ValidationResult with errors and warnings.
        """
        self._errors = []
        self._warnings = []

        self._validate_timestamps(output)
        self._validate_confidence(output)
        self._validate_content(output)
        self._validate_consistency(output)

        return ValidationResult(
            is_valid=len(self._errors) == 0,
            errors=self._errors.copy(),
            warnings=self._warnings.copy(),
        )

    def _validate_timestamps(self, output: HistorianOutput) -> None:
        """Validate timestamp fields."""
        now = datetime.now(timezone.utc)

        # first_seen_at should not be in the future
        if output.first_seen_at.replace(tzinfo=timezone.utc) > now:
            self._errors.append("first_seen_at is in the future")

        # first_seen_at should be <= last_seen_at
        if output.first_seen_at > output.last_seen_at:
            self._errors.append("first_seen_at is after last_seen_at")

        # Check timeline points are in order
        if output.timeline_points:
            prev_time = None
            for i, tp in enumerate(output.timeline_points):
                if prev_time and tp.event_time < prev_time:
                    self._warnings.append(
                        f"Timeline point {i} is out of order"
                    )
                prev_time = tp.event_time

    def _validate_confidence(self, output: HistorianOutput) -> None:
        """Validate confidence score."""
        if not 0 <= output.historical_confidence <= 1:
            self._errors.append(
                f"historical_confidence out of range: {output.historical_confidence}"
            )

        # Low confidence warning
        if output.historical_confidence < 0.3:
            self._warnings.append(
                f"Low confidence score: {output.historical_confidence:.2f}"
            )

    def _validate_content(self, output: HistorianOutput) -> None:
        """Validate content fields."""
        # history_summary should not be empty for non-new topics
        if output.historical_status != HistoricalStatus.NEW:
            if not output.history_summary:
                self._errors.append(
                    "history_summary is empty for non-new topic"
                )

        # what_is_new_this_time should not be empty
        if not output.what_is_new_this_time:
            self._warnings.append("what_is_new_this_time is empty")

        # Check for placeholder text
        placeholder_patterns = [
            "TODO",
            "PLACEHOLDER",
            "[INSERT",
            "{{",
            "}}",
        ]
        for pattern in placeholder_patterns:
            if output.history_summary and pattern in output.history_summary:
                self._errors.append(
                    f"history_summary contains placeholder: {pattern}"
                )
            if output.what_is_new_this_time and pattern in output.what_is_new_this_time:
                self._errors.append(
                    f"what_is_new_this_time contains placeholder: {pattern}"
                )

    def _validate_consistency(self, output: HistorianOutput) -> None:
        """Validate consistency between fields."""
        # Timeline present but no history summary
        if output.timeline_points and not output.history_summary:
            self._warnings.append(
                "timeline_points present but history_summary is empty"
            )

        # New status but has timeline
        if output.historical_status == HistoricalStatus.NEW:
            if len(output.timeline_points) > 1:
                self._warnings.append(
                    "Status is 'new' but has multiple timeline points"
                )

        # Milestone status but no what's new
        if output.historical_status == HistoricalStatus.MILESTONE:
            if not output.what_is_new_this_time:
                self._errors.append(
                    "Status is 'milestone' but what_is_new_this_time is empty"
                )

        # Similar topics but no background
        if output.similar_past_topics and not output.important_background:
            self._warnings.append(
                "Has similar_past_topics but no important_background"
            )


class ValidationResult:
    """Result of validation."""

    def __init__(
        self,
        is_valid: bool,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        """Initialize the result.

        Args:
            is_valid: Whether validation passed.
            errors: List of error messages.
            warnings: List of warning messages.
        """
        self.is_valid = is_valid
        self.errors = errors
        self.warnings = warnings

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ValidationResult(is_valid={self.is_valid}, "
            f"errors={len(self.errors)}, warnings={len(self.warnings)})"
        )


def validate_historian_output(output: HistorianOutput) -> ValidationResult:
    """Validate historian output.

    Convenience function for quick validation.

    Args:
        output: HistorianOutput to validate.

    Returns:
        ValidationResult.
    """
    validator = HistorianValidator()
    return validator.validate(output)
