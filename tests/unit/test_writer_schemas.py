"""Tests for Writer Agent schemas."""

import pytest
from datetime import datetime

from app.agents.writer.schemas import (
    CopyType,
    FeedCardCopyDTO,
    TopicIntroCopyDTO,
    TrendCardCopyDTO,
    ReportSectionCopyDTO,
    WriterOutput,
    WriterInput,
)


class TestCopyType:
    """Tests for CopyType enum."""

    def test_copy_types(self):
        """Test all copy types exist."""
        assert CopyType.FEED_CARD == "feed_card"
        assert CopyType.TOPIC_INTRO == "topic_intro"
        assert CopyType.TREND_CARD == "trend_card"
        assert CopyType.REPORT_SECTION == "report_section"


class TestFeedCardCopyDTO:
    """Tests for FeedCardCopyDTO."""

    def test_create_feed_card(self):
        """Test creating a feed card copy."""
        card = FeedCardCopyDTO(
            title="Test Title",
            short_summary="This is a test summary.",
            why_it_matters_short="Important for testing.",
            display_tags=["test", "demo"],
            audience_hint="Developers",
        )
        assert card.title == "Test Title"
        assert card.short_summary == "This is a test summary."
        assert len(card.display_tags) == 2

    def test_feed_card_defaults(self):
        """Test feed card default values."""
        card = FeedCardCopyDTO(
            title="Test",
            short_summary="Summary",
            why_it_matters_short="Matters",
        )
        assert card.display_tags == []
        assert card.audience_hint is None
        assert card.call_to_action is None


class TestTopicIntroCopyDTO:
    """Tests for TopicIntroCopyDTO."""

    def test_create_topic_intro(self):
        """Test creating a topic intro copy."""
        intro = TopicIntroCopyDTO(
            headline="Test Headline",
            intro="This is the introduction paragraph.",
            key_takeaways=["Point 1", "Point 2", "Point 3"],
            why_it_matters="This is important because...",
            what_changed_now="Recent developments include...",
        )
        assert intro.headline == "Test Headline"
        assert len(intro.key_takeaways) == 3

    def test_topic_intro_defaults(self):
        """Test topic intro default values."""
        intro = TopicIntroCopyDTO(
            headline="Test",
            intro="Intro",
            why_it_matters="Matters",
            what_changed_now="Changed",
        )
        assert intro.key_takeaways == []
        assert intro.background_context is None
        assert intro.related_reading_hints == []


class TestTrendCardCopyDTO:
    """Tests for TrendCardCopyDTO."""

    def test_create_trend_card(self):
        """Test creating a trend card copy."""
        card = TrendCardCopyDTO(
            trend_title="Emerging Trend",
            trend_summary="This trend is growing.",
            signal_summary="Multiple signals detected.",
            stage_label="rising",
        )
        assert card.trend_title == "Emerging Trend"
        assert card.stage_label == "rising"


class TestReportSectionCopyDTO:
    """Tests for ReportSectionCopyDTO."""

    def test_create_report_section(self):
        """Test creating a report section copy."""
        section = ReportSectionCopyDTO(
            section_title="Top Stories",
            section_intro="Today's top stories.",
            key_points=["Point 1", "Point 2"],
        )
        assert section.section_title == "Top Stories"
        assert len(section.key_points) == 2


class TestWriterOutput:
    """Tests for WriterOutput."""

    def test_create_writer_output_feed_card(self):
        """Test creating writer output with feed card."""
        feed_card = FeedCardCopyDTO(
            title="Test",
            short_summary="Summary",
            why_it_matters_short="Matters",
        )
        output = WriterOutput(
            copy_type=CopyType.FEED_CARD,
            topic_id=1,
            feed_card=feed_card,
        )
        assert output.copy_type == CopyType.FEED_CARD
        assert output.get_copy() == feed_card

    def test_create_writer_output_topic_intro(self):
        """Test creating writer output with topic intro."""
        intro = TopicIntroCopyDTO(
            headline="Test",
            intro="Intro",
            why_it_matters="Matters",
            what_changed_now="Changed",
        )
        output = WriterOutput(
            copy_type=CopyType.TOPIC_INTRO,
            topic_id=1,
            topic_intro=intro,
        )
        assert output.copy_type == CopyType.TOPIC_INTRO
        assert output.get_copy() == intro

    def test_writer_output_defaults(self):
        """Test writer output default values."""
        output = WriterOutput(
            copy_type=CopyType.FEED_CARD,
            topic_id=1,
        )
        assert output.prompt_version == "v1"
        assert output.source_agent == "writer"
        assert output.confidence == 0.8


class TestWriterInput:
    """Tests for WriterInput."""

    def test_create_writer_input(self):
        """Test creating writer input."""
        input_data = WriterInput(
            topic_id=1,
            copy_type=CopyType.FEED_CARD,
            topic_title="Test Topic",
            topic_summary="Test summary",
            tags=["tag1", "tag2"],
        )
        assert input_data.topic_id == 1
        assert input_data.copy_type == CopyType.FEED_CARD
        assert len(input_data.tags) == 2

    def test_writer_input_defaults(self):
        """Test writer input default values."""
        input_data = WriterInput(
            topic_id=1,
            copy_type=CopyType.FEED_CARD,
            topic_title="Test",
        )
        assert input_data.topic_summary is None
        assert input_data.tags == []
        assert input_data.item_count == 0
        assert input_data.heat_score == 0.0
