"""Tests for Reviewer Agent schemas and validators."""

import pytest

from app.agents.reviewer.schemas import (
    ReviewStatus,
    ReviewIssue,
    ReviewerOutput,
    ReviewerInput,
)
from app.agents.reviewer.rubric import (
    ReviewRubric,
    RubricItem,
    get_rubric,
)
from app.editorial.validators.copy_guard import CopyGuard, CopyGuardIssue
from app.editorial.validators.fact_guard import FactGuard, FactGuardIssue


class TestReviewStatus:
    """Tests for ReviewStatus enum."""

    def test_review_statuses(self):
        """Test all review statuses exist."""
        assert ReviewStatus.APPROVE == "approve"
        assert ReviewStatus.REVISE == "revise"
        assert ReviewStatus.REJECT == "reject"


class TestReviewIssue:
    """Tests for ReviewIssue."""

    def test_create_review_issue(self):
        """Test creating a review issue."""
        issue = ReviewIssue(
            issue_type="factual_drift",
            severity="major",
            description="Content drifts from source",
            field="summary",
            suggestion="Align with historian output",
        )
        assert issue.issue_type == "factual_drift"
        assert issue.severity == "major"


class TestReviewerOutput:
    """Tests for ReviewerOutput."""

    def test_create_reviewer_output_approve(self):
        """Test creating approved review output."""
        output = ReviewerOutput(
            review_status=ReviewStatus.APPROVE,
            confidence=0.9,
        )
        assert output.review_status == ReviewStatus.APPROVE
        assert output.issues == []

    def test_create_reviewer_output_revise(self):
        """Test creating revise review output."""
        output = ReviewerOutput(
            review_status=ReviewStatus.REVISE,
            issues=[
                ReviewIssue(
                    issue_type="vague_summary",
                    severity="minor",
                    description="Summary is too vague",
                ),
            ],
            revision_hints=["Add specific details"],
            confidence=0.7,
        )
        assert output.review_status == ReviewStatus.REVISE
        assert len(output.issues) == 1
        assert len(output.revision_hints) == 1


class TestReviewerInput:
    """Tests for ReviewerInput."""

    def test_create_reviewer_input(self):
        """Test creating reviewer input."""
        input_data = ReviewerInput(
            topic_id=1,
            copy_type="topic_intro",
            copy_body={
                "headline": "Test Headline",
                "intro": "Test intro paragraph.",
            },
        )
        assert input_data.topic_id == 1
        assert input_data.copy_type == "topic_intro"


class TestReviewRubric:
    """Tests for ReviewRubric."""

    def test_get_rubric(self):
        """Test getting rubric for copy type."""
        rubric = get_rubric("feed_card")
        assert len(rubric.items) > 0

    def test_rubric_has_required_checks(self):
        """Test rubric has required check types."""
        rubric = get_rubric("topic_intro")
        issue_types = [item.issue_type for item in rubric.items]
        
        # Check for expected issue types
        assert any("factual" in str(t).lower() for t in issue_types)
        assert any("unsupported" in str(t).lower() for t in issue_types)
        assert any("vague" in str(t).lower() for t in issue_types)


class TestCopyGuard:
    """Tests for CopyGuard validator."""

    def test_validate_feed_card_valid(self):
        """Test validating a valid feed card."""
        guard = CopyGuard()
        issues = guard.validate(
            {
                "title": "This is a valid title for testing",
                "short_summary": "This is a valid summary that is long enough to pass validation.",
            },
            "feed_card",
        )
        # Should have no critical issues
        critical = [i for i in issues if i.severity == "critical"]
        assert len(critical) == 0

    def test_validate_feed_card_missing_field(self):
        """Test validating feed card with missing field."""
        guard = CopyGuard()
        issues = guard.validate(
            {
                "title": "Test Title",
                # missing short_summary
            },
            "feed_card",
        )
        missing = [i for i in issues if i.issue_type == "missing_field"]
        assert len(missing) > 0

    def test_validate_feed_card_too_short(self):
        """Test validating feed card with short content."""
        guard = CopyGuard()
        issues = guard.validate(
            {
                "title": "Short",  # Too short
                "short_summary": "OK summary that is long enough.",
            },
            "feed_card",
        )
        short = [i for i in issues if i.issue_type == "too_short"]
        assert len(short) > 0

    def test_detect_vague_language(self):
        """Test detecting vague language."""
        guard = CopyGuard()
        issues = guard.validate(
            {
                "title": "Important development in tech",  # Contains vague phrase
                "short_summary": "This is a significant progress in the field.",
            },
            "feed_card",
        )
        vague = [i for i in issues if i.issue_type == "vague_language"]
        assert len(vague) > 0


class TestFactGuard:
    """Tests for FactGuard validator."""

    def test_validate_valid_content(self):
        """Test validating valid content."""
        guard = FactGuard()
        issues = guard.validate(
            {"item_count": 10, "source_count": 5},
        )
        assert len(issues) == 0

    def test_validate_negative_metrics(self):
        """Test detecting negative metrics."""
        guard = FactGuard()
        issues = guard.validate(
            {"item_count": -1},
        )
        invalid = [i for i in issues if i.issue_type == "invalid_metric"]
        assert len(invalid) > 0

    def test_validate_invalid_score_range(self):
        """Test detecting invalid score range."""
        guard = FactGuard()
        issues = guard.validate(
            {"heat_score": 1.5},  # Should be 0-1
        )
        invalid = [i for i in issues if i.issue_type == "invalid_metric"]
        assert len(invalid) > 0

    def test_validate_timeline_order(self):
        """Test validating timeline order."""
        from datetime import datetime, timedelta
        
        guard = FactGuard()
        now = datetime.utcnow()
        
        # Out of order timeline
        issues = guard.validate(
            {},
            timeline_points=[
                {"event_time": now},
                {"event_time": now - timedelta(days=1)},  # Earlier than previous
            ],
        )
        order_issues = [i for i in issues if i.issue_type == "timeline_order"]
        assert len(order_issues) > 0
