"""Unit tests for processing pipeline."""

import pytest

from app.common.enums import BoardType, ContentType
from app.contracts.dto.normalized_item import NormalizedItemDTO
from app.contracts.dto.raw_item import RawItemDTO
from app.processing.pipeline import (
    PipelineResult,
    ProcessingPipeline,
    process_raw_items,
    process_single_item,
)


# ---------------------------------------------------------------------------
# Sample content
# ---------------------------------------------------------------------------

SAMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Test Article About AI</title>
    <meta name="author" content="John Doe">
</head>
<body>
    <h1>Test Article About AI</h1>
    <p>This is a comprehensive article about artificial intelligence and machine learning.</p>
    <p>We explore deep learning, neural networks, and natural language processing.</p>
</body>
</html>"""

SAMPLE_JSON = {
    "title": "GitHub Release v1.0",
    "body": "Release notes for version 1.0 with new features and bug fixes.",
    "html_url": "https://github.com/owner/repo/releases/tag/v1.0",
    "author": {"login": "developer"},
    "published_at": "2026-04-10T12:00:00Z",
    "stargazers_count": 100,
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _make_raw_item(
    item_id: int = 1,
    raw_html: str | None = None,
    raw_json: dict | None = None,
    raw_text: str | None = None,
    url: str = "https://example.com/article",
) -> RawItemDTO:
    return RawItemDTO(
        id=item_id,
        source_id=1,
        url=url,
        canonical_url=url,
        raw_html=raw_html,
        raw_json=raw_json,
        raw_text=raw_text,
    )


# ---------------------------------------------------------------------------
# ProcessingPipeline Tests
# ---------------------------------------------------------------------------


class TestProcessingPipeline:
    def test_process_html_items(self) -> None:
        pipeline = ProcessingPipeline()
        raw_items = [
            _make_raw_item(item_id=1, raw_html=SAMPLE_HTML, url="https://example.com/1"),
            _make_raw_item(item_id=2, raw_html=SAMPLE_HTML, url="https://example.com/2"),
        ]

        result = pipeline.process(raw_items, skip_dedup=True)

        assert isinstance(result, PipelineResult)
        assert result.total_input == 2
        assert result.parsed_count == 2
        assert result.normalized_count == 2
        assert len(result.items) == 2
        assert result.items[0].title == "Test Article About AI"

    def test_process_json_items(self) -> None:
        pipeline = ProcessingPipeline()
        raw_items = [
            _make_raw_item(item_id=1, raw_json=SAMPLE_JSON, url="https://github.com/1"),
        ]

        result = pipeline.process(raw_items, content_type=ContentType.REPOSITORY, skip_dedup=True)

        assert result.parsed_count == 1
        assert result.normalized_count == 1
        assert len(result.items) == 1
        # JSON parser extracts content, title may be cleaned/normalized
        assert result.items[0].clean_text != ""

    def test_process_with_dedup(self) -> None:
        pipeline = ProcessingPipeline()
        # Two items with same URL should be deduplicated
        raw_items = [
            _make_raw_item(item_id=1, raw_html=SAMPLE_HTML, url="https://example.com/same"),
            _make_raw_item(item_id=2, raw_html=SAMPLE_HTML, url="https://example.com/same"),
        ]

        result = pipeline.process(raw_items)

        assert result.total_input == 2
        assert result.deduplicated_count == 1
        assert len(result.duplicates) == 1

    def test_process_against_existing(self) -> None:
        pipeline = ProcessingPipeline()
        existing = [
            NormalizedItemDTO(
                id=100,
                source_id=1,
                title="Existing",
                clean_text="Existing content",
                canonical_url="https://example.com/existing",
                content_type=ContentType.ARTICLE,
                board_type_candidate=BoardType.GENERAL,
            )
        ]
        raw_items = [
            _make_raw_item(item_id=1, raw_html=SAMPLE_HTML, url="https://example.com/new"),
            _make_raw_item(item_id=2, raw_html=SAMPLE_HTML, url="https://example.com/existing"),
        ]

        result = pipeline.process(raw_items, existing_items=existing)

        # One new, one duplicate of existing
        assert result.deduplicated_count == 1
        assert len(result.duplicates) == 1

    def test_process_empty_list(self) -> None:
        pipeline = ProcessingPipeline()
        result = pipeline.process([])

        assert result.total_input == 0
        assert result.parsed_count == 0
        assert len(result.items) == 0

    def test_process_unparseable_item(self) -> None:
        pipeline = ProcessingPipeline()
        raw_items = [
            _make_raw_item(item_id=1),  # No content
        ]

        result = pipeline.process(raw_items)

        assert result.total_input == 1
        assert result.parsed_count == 0
        assert result.failed_count == 1
        assert len(result.errors) > 0

    def test_process_single(self) -> None:
        pipeline = ProcessingPipeline()
        raw_item = _make_raw_item(item_id=1, raw_html=SAMPLE_HTML)

        normalized, parse_result = pipeline.process_single(raw_item)

        assert normalized is not None
        assert parse_result.success is True
        assert normalized.title == "Test Article About AI"

    def test_process_single_failure(self) -> None:
        pipeline = ProcessingPipeline()
        raw_item = _make_raw_item(item_id=1)  # No content

        normalized, parse_result = pipeline.process_single(raw_item)

        assert normalized is None
        assert parse_result.success is False

    def test_board_type_inference(self) -> None:
        pipeline = ProcessingPipeline()
        raw_items = [
            _make_raw_item(item_id=1, raw_html=SAMPLE_HTML, url="https://example.com/ai"),
        ]

        result = pipeline.process(raw_items, skip_dedup=True)

        # Content mentions AI/ML, should be classified as AI board
        assert len(result.items) == 1
        assert result.items[0].board_type_candidate == BoardType.AI

    def test_quality_score_calculated(self) -> None:
        pipeline = ProcessingPipeline()
        raw_items = [
            _make_raw_item(item_id=1, raw_html=SAMPLE_HTML, url="https://example.com/1"),
        ]

        result = pipeline.process(raw_items, skip_dedup=True)

        assert len(result.items) == 1
        assert result.items[0].quality_score > 0


# ---------------------------------------------------------------------------
# Module function tests
# ---------------------------------------------------------------------------


class TestModuleFunctions:
    def test_process_raw_items(self) -> None:
        raw_items = [
            _make_raw_item(item_id=1, raw_html=SAMPLE_HTML, url="https://example.com/1"),
        ]

        result = process_raw_items(raw_items, skip_dedup=True)

        assert result.total_input == 1
        assert len(result.items) == 1

    def test_process_single_item(self) -> None:
        raw_item = _make_raw_item(item_id=1, raw_html=SAMPLE_HTML)

        normalized, parse_result = process_single_item(raw_item)

        assert normalized is not None
        assert parse_result.success is True
