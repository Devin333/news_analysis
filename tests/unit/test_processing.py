"""Unit tests for cleaner and normalizer."""

from datetime import datetime, timezone

import pytest

from app.common.enums import BoardType, ContentType
from app.contracts.dto.normalized_item import NormalizedItemDTO
from app.contracts.dto.parse_result import ParseResult
from app.contracts.dto.raw_item import RawItemDTO
from app.processing.cleaner import TextCleaner, TitleCleaner, clean_text, clean_title
from app.processing.normalizer import ContentNormalizer, normalize_content


# ---------------------------------------------------------------------------
# TextCleaner Tests
# ---------------------------------------------------------------------------


class TestTextCleaner:
    def test_default_clean(self) -> None:
        text = "  Hello   World  \n\n\n\nTest  "
        result = clean_text(text)
        # Whitespace normalization collapses spaces but may leave trailing before newline
        assert "Hello" in result
        assert "World" in result
        assert "Test" in result
        assert "\n\n\n" not in result

    def test_unicode_normalization(self) -> None:
        cleaner = TextCleaner(normalize_unicode=True)
        # Full-width characters
        text = "Ｈｅｌｌｏ"
        result = cleaner.clean(text)
        assert result == "Hello"

    def test_control_char_removal(self) -> None:
        cleaner = TextCleaner(remove_control_chars=True)
        text = "Hello\x00World\x1fTest"
        result = cleaner.clean(text)
        assert "\x00" not in result
        assert "\x1f" not in result
        assert "HelloWorldTest" in result

    def test_url_masking(self) -> None:
        cleaner = TextCleaner(mask_urls=True)
        text = "Visit https://example.com for more info"
        result = cleaner.clean(text)
        assert "[URL]" in result
        assert "https://example.com" not in result

    def test_email_masking(self) -> None:
        cleaner = TextCleaner(mask_emails=True)
        text = "Contact us at test@example.com"
        result = cleaner.clean(text)
        assert "[EMAIL]" in result
        assert "test@example.com" not in result

    def test_max_length(self) -> None:
        cleaner = TextCleaner(max_length=10)
        text = "This is a very long text"
        result = cleaner.clean(text)
        assert len(result) <= 10

    def test_empty_text(self) -> None:
        result = clean_text("")
        assert result == ""

    def test_whitespace_normalization(self) -> None:
        cleaner = TextCleaner(normalize_whitespace=True)
        text = "Hello    World\n\n\n\n\nTest"
        result = cleaner.clean(text)
        assert "    " not in result
        assert "\n\n\n" not in result


# ---------------------------------------------------------------------------
# TitleCleaner Tests
# ---------------------------------------------------------------------------


class TestTitleCleaner:
    def test_default_clean(self) -> None:
        title = "  Article Title  "
        result = clean_title(title)
        assert result == "Article Title"

    def test_remove_site_suffix(self) -> None:
        cleaner = TitleCleaner(remove_site_name=True)
        title = "Article Title - Example Site"
        result = cleaner.clean(title)
        assert result == "Article Title"

    def test_remove_pipe_suffix(self) -> None:
        cleaner = TitleCleaner(remove_site_name=True)
        title = "Article Title | Example Site"
        result = cleaner.clean(title)
        assert result == "Article Title"

    def test_max_length(self) -> None:
        cleaner = TitleCleaner(max_length=20)
        title = "This is a very long article title that should be truncated"
        result = cleaner.clean(title)
        assert len(result) <= 20
        assert result.endswith("...")

    def test_capitalize(self) -> None:
        cleaner = TitleCleaner(capitalize=True)
        title = "lowercase title"
        result = cleaner.clean(title)
        assert result[0].isupper()

    def test_whitespace_normalization(self) -> None:
        title = "Title   with   spaces"
        result = clean_title(title)
        assert "   " not in result


# ---------------------------------------------------------------------------
# ContentNormalizer Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_raw_item() -> RawItemDTO:
    return RawItemDTO(
        id=1,
        source_id=1,
        url="https://example.com/article",
        canonical_url="https://example.com/article",
    )


@pytest.fixture
def sample_parse_result() -> ParseResult:
    return ParseResult(
        success=True,
        title="Test Article About Machine Learning",
        clean_text="This is a comprehensive article about machine learning and artificial intelligence. " * 20,
        excerpt="This is a comprehensive article about machine learning...",
        author="John Doe",
        published_at=datetime(2026, 4, 10, 12, 0, 0, tzinfo=timezone.utc),
        language="en",
        tags=["ai", "machine learning", "python"],
        images=["https://example.com/image.jpg"],
        links=["https://example.com/link1"],
        word_count=200,
        reading_time_minutes=1,
    )


class TestContentNormalizer:
    def test_normalize_basic(
        self, sample_raw_item: RawItemDTO, sample_parse_result: ParseResult
    ) -> None:
        result = normalize_content(sample_raw_item, sample_parse_result)

        assert isinstance(result, NormalizedItemDTO)
        assert result.title == "Test Article About Machine Learning"
        assert result.source_id == 1
        assert result.raw_item_id == 1
        assert result.author == "John Doe"
        assert result.language == "en"

    def test_infer_ai_board(
        self, sample_raw_item: RawItemDTO, sample_parse_result: ParseResult
    ) -> None:
        normalizer = ContentNormalizer(infer_board_type=True)
        result = normalizer.normalize(sample_raw_item, sample_parse_result)

        assert result.board_type_candidate == BoardType.AI

    def test_infer_engineering_board(self, sample_raw_item: RawItemDTO) -> None:
        parse_result = ParseResult(
            success=True,
            title="Building Microservices with Kubernetes",
            clean_text="This article covers software engineering best practices for building microservices with Docker and Kubernetes. " * 10,
            word_count=100,
            reading_time_minutes=1,
            tags=["kubernetes", "docker", "devops"],
        )
        normalizer = ContentNormalizer(infer_board_type=True)
        result = normalizer.normalize(sample_raw_item, parse_result)

        assert result.board_type_candidate == BoardType.ENGINEERING

    def test_infer_research_board(self, sample_raw_item: RawItemDTO) -> None:
        parse_result = ParseResult(
            success=True,
            title="A Research Paper on Novel Methodology",
            clean_text="This research paper presents findings from our experiment. The methodology and analysis are peer reviewed. " * 10,
            word_count=100,
            reading_time_minutes=1,
            tags=["research", "paper", "arxiv"],
        )
        normalizer = ContentNormalizer(infer_board_type=True)
        result = normalizer.normalize(sample_raw_item, parse_result)

        assert result.board_type_candidate == BoardType.RESEARCH

    def test_quality_score_high(
        self, sample_raw_item: RawItemDTO, sample_parse_result: ParseResult
    ) -> None:
        normalizer = ContentNormalizer(calculate_quality=True)
        result = normalizer.normalize(sample_raw_item, sample_parse_result)

        # Should have high quality score with all fields present
        assert result.quality_score >= 0.7

    def test_quality_score_low(self, sample_raw_item: RawItemDTO) -> None:
        parse_result = ParseResult(
            success=True,
            title="Short",
            clean_text="Very short content.",
            word_count=3,
            reading_time_minutes=1,
        )
        normalizer = ContentNormalizer(calculate_quality=True)
        result = normalizer.normalize(sample_raw_item, parse_result)

        # Should have low quality score
        assert result.quality_score < 0.5

    def test_content_type_preserved(
        self, sample_raw_item: RawItemDTO, sample_parse_result: ParseResult
    ) -> None:
        result = normalize_content(
            sample_raw_item, sample_parse_result, content_type=ContentType.PAPER
        )

        assert result.content_type == ContentType.PAPER

    def test_metadata_included(
        self, sample_raw_item: RawItemDTO, sample_parse_result: ParseResult
    ) -> None:
        result = normalize_content(sample_raw_item, sample_parse_result)

        assert "word_count" in result.metadata_json
        assert "reading_time_minutes" in result.metadata_json
        assert "tags" in result.metadata_json
        assert result.metadata_json["word_count"] == 200

    def test_canonical_url_fallback(self, sample_parse_result: ParseResult) -> None:
        raw_item = RawItemDTO(
            id=1,
            source_id=1,
            url="https://example.com/article",
            canonical_url=None,
        )
        result = normalize_content(raw_item, sample_parse_result)

        assert result.canonical_url == "https://example.com/article"

    def test_generate_excerpt_when_missing(self, sample_raw_item: RawItemDTO) -> None:
        parse_result = ParseResult(
            success=True,
            title="Test",
            clean_text="This is the content that should be used to generate an excerpt automatically.",
            excerpt=None,
            word_count=15,
            reading_time_minutes=1,
        )
        result = normalize_content(sample_raw_item, parse_result)

        assert result.excerpt is not None
        assert len(result.excerpt) > 0
