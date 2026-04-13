"""Tests for rule-based tagger and tag service."""

import pytest

from app.contracts.dto.tag import TagType
from app.processing.tagging.rule_tagger import (
    RuleTagger,
    TaggerConfig,
    TaggingContext,
)
from app.processing.tagging.tag_service import TagService, TagServiceConfig


class TestRuleTagger:
    """Tests for RuleTagger."""

    def test_tagger_initialization(self):
        """Test tagger initializes with compiled patterns."""
        tagger = RuleTagger()
        counts = tagger.get_pattern_count()

        assert "company" in counts
        assert "framework" in counts
        assert "model" in counts
        assert counts["company"] > 0
        assert counts["framework"] > 0

    def test_tag_company_openai(self):
        """Test tagging OpenAI company."""
        tagger = RuleTagger()
        context = TaggingContext(
            title="OpenAI releases GPT-5",
            excerpt="",
            clean_text="",
        )
        result = tagger.tag(context)

        company_tags = [t for t in result.matches if t.tag_type == TagType.COMPANY]
        assert len(company_tags) >= 1
        assert any(t.tag_name == "OpenAI" for t in company_tags)

    def test_tag_company_alias(self):
        """Test tagging company by alias."""
        tagger = RuleTagger()
        context = TaggingContext(
            title="DeepMind announces new research",
            excerpt="",
            clean_text="",
        )
        result = tagger.tag(context)

        company_tags = [t for t in result.matches if t.tag_type == TagType.COMPANY]
        assert len(company_tags) >= 1
        # DeepMind is an alias for Google
        assert any(t.tag_name == "Google" for t in company_tags)

    def test_tag_framework_pytorch(self):
        """Test tagging PyTorch framework."""
        tagger = RuleTagger()
        context = TaggingContext(
            title="PyTorch 2.0 released with new features",
            excerpt="",
            clean_text="",
        )
        result = tagger.tag(context)

        framework_tags = [t for t in result.matches if t.tag_type == TagType.FRAMEWORK]
        assert len(framework_tags) >= 1
        assert any(t.tag_name == "PyTorch" for t in framework_tags)

    def test_tag_model_gpt4(self):
        """Test tagging GPT-4 model."""
        tagger = RuleTagger()
        context = TaggingContext(
            title="GPT-4 achieves new benchmark",
            excerpt="",
            clean_text="",
        )
        result = tagger.tag(context)

        model_tags = [t for t in result.matches if t.tag_type == TagType.MODEL]
        assert len(model_tags) >= 1
        assert any(t.tag_name == "GPT-4" for t in model_tags)

    def test_tag_model_claude(self):
        """Test tagging Claude model."""
        tagger = RuleTagger()
        context = TaggingContext(
            title="Claude 3 Opus performance analysis",
            excerpt="",
            clean_text="",
        )
        result = tagger.tag(context)

        model_tags = [t for t in result.matches if t.tag_type == TagType.MODEL]
        assert len(model_tags) >= 1
        assert any(t.tag_name == "Claude" for t in model_tags)

    def test_tag_task_rag(self):
        """Test tagging RAG task."""
        tagger = RuleTagger()
        context = TaggingContext(
            title="Building RAG applications with LangChain",
            excerpt="",
            clean_text="",
        )
        result = tagger.tag(context)

        task_tags = [t for t in result.matches if t.tag_type == TagType.TASK]
        assert len(task_tags) >= 1
        assert any(t.tag_name == "RAG" for t in task_tags)

    def test_tag_domain_nlp(self):
        """Test tagging NLP domain."""
        tagger = RuleTagger()
        context = TaggingContext(
            title="Advances in natural language processing",
            excerpt="",
            clean_text="",
        )
        result = tagger.tag(context)

        domain_tags = [t for t in result.matches if t.tag_type == TagType.TECHNOLOGY_DOMAIN]
        assert len(domain_tags) >= 1
        assert any(t.tag_name == "NLP" for t in domain_tags)

    def test_tag_multiple_entities(self):
        """Test tagging multiple entities in one text."""
        tagger = RuleTagger()
        context = TaggingContext(
            title="OpenAI and Google compete in LLM space",
            excerpt="GPT-4 vs Gemini comparison",
            clean_text="",
        )
        result = tagger.tag(context)

        company_tags = [t for t in result.matches if t.tag_type == TagType.COMPANY]
        model_tags = [t for t in result.matches if t.tag_type == TagType.MODEL]

        assert len(company_tags) >= 2
        assert len(model_tags) >= 2

    def test_tag_case_insensitive(self):
        """Test case insensitive matching."""
        tagger = RuleTagger()
        context = TaggingContext(
            title="OPENAI releases new model",
            excerpt="",
            clean_text="",
        )
        result = tagger.tag(context)

        company_tags = [t for t in result.matches if t.tag_type == TagType.COMPANY]
        assert any(t.tag_name == "OpenAI" for t in company_tags)

    def test_tag_text_convenience(self):
        """Test tag_text convenience method."""
        tagger = RuleTagger()
        result = tagger.tag_text("PyTorch and TensorFlow are popular frameworks")

        framework_tags = [t for t in result.matches if t.tag_type == TagType.FRAMEWORK]
        assert len(framework_tags) >= 2

    def test_tag_title_boost(self):
        """Test that title matches get confidence boost."""
        tagger = RuleTagger()

        # Match in title
        context1 = TaggingContext(
            title="OpenAI news",
            excerpt="",
            clean_text="",
        )
        result1 = tagger.tag(context1)

        # Match only in body
        context2 = TaggingContext(
            title="Tech news",
            excerpt="",
            clean_text="OpenAI announced something",
        )
        result2 = tagger.tag(context2)

        openai1 = next((t for t in result1.matches if t.tag_name == "OpenAI"), None)
        openai2 = next((t for t in result2.matches if t.tag_name == "OpenAI"), None)

        assert openai1 is not None
        assert openai2 is not None
        assert openai1.confidence >= openai2.confidence

    def test_max_tags_per_type(self):
        """Test limiting tags per type."""
        config = TaggerConfig(max_tags_per_type=2)
        tagger = RuleTagger(config=config)

        # Text with many companies
        context = TaggingContext(
            title="OpenAI Google Microsoft Meta Amazon news",
            excerpt="",
            clean_text="",
        )
        result = tagger.tag(context)

        company_tags = [t for t in result.matches if t.tag_type == TagType.COMPANY]
        assert len(company_tags) <= 2

    def test_min_confidence_filter(self):
        """Test minimum confidence filtering."""
        config = TaggerConfig(min_confidence=0.9)
        tagger = RuleTagger(config=config)

        context = TaggingContext(
            title="",
            excerpt="",
            clean_text="openai mentioned somewhere",
        )
        result = tagger.tag(context)

        # Low confidence matches should be filtered
        # (body-only match without title boost)
        assert all(t.confidence >= 0.9 for t in result.matches)

    def test_empty_input(self):
        """Test handling empty input."""
        tagger = RuleTagger()
        context = TaggingContext(
            title="",
            excerpt="",
            clean_text="",
        )
        result = tagger.tag(context)

        assert result.matches == []
        assert result.processing_time_ms >= 0

    def test_no_matches(self):
        """Test text with no matching patterns."""
        tagger = RuleTagger()
        context = TaggingContext(
            title="Weather forecast for tomorrow",
            excerpt="Sunny with clouds",
            clean_text="Temperature around 20 degrees",
        )
        result = tagger.tag(context)

        # Should have no AI-related tags
        assert len(result.matches) == 0


class TestTagService:
    """Tests for TagService."""

    def test_service_initialization(self):
        """Test service initializes correctly."""
        service = TagService()
        assert service is not None

    def test_tag_item(self):
        """Test tagging a normalized item."""
        from datetime import datetime, timezone
        from app.contracts.dto.normalized_item import NormalizedItemDTO
        from app.common.enums import ContentType

        service = TagService()

        item = NormalizedItemDTO(
            id=1,
            raw_item_id=1,
            source_id=1,
            title="OpenAI releases GPT-4 Turbo",
            clean_text="New model with improved performance",
            excerpt="GPT-4 Turbo announcement",
            published_at=datetime.now(timezone.utc),
            content_type=ContentType.ARTICLE,
        )

        result = service.tag_item(item)

        assert result.success
        assert result.item_id == 1
        assert len(result.tags) > 0
        assert any(t.tag_name == "OpenAI" for t in result.tags)
        assert any(t.tag_name == "GPT-4" for t in result.tags)

    def test_tag_topic(self):
        """Test tagging a topic."""
        from datetime import datetime, timezone
        from app.contracts.dto.topic import TopicReadDTO
        from app.common.enums import BoardType

        service = TagService()

        topic = TopicReadDTO(
            id=1,
            board_type=BoardType.AI,
            topic_type="auto",
            title="LangChain framework updates",
            summary="New features in LangChain for RAG applications",
            representative_item_id=None,
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
            item_count=5,
            source_count=3,
            heat_score=50.0,
            trend_score=0.0,
            status="active",
            metadata_json={},
        )

        result = service.tag_topic(topic)

        assert result.success
        assert result.topic_id == 1
        assert len(result.tags) > 0
        assert any(t.tag_name == "LangChain" for t in result.tags)
        assert any(t.tag_name == "RAG" for t in result.tags)

    def test_tag_text(self):
        """Test tagging plain text."""
        service = TagService()
        result = service.tag_text("PyTorch 2.0 brings new features for deep learning")

        assert result.success
        assert len(result.tags) > 0
        assert any(t.tag_name == "PyTorch" for t in result.tags)

    def test_to_item_tags(self):
        """Test converting matches to item tags."""
        from app.contracts.dto.tag import TagMatchDTO, TagType

        service = TagService()
        matches = [
            TagMatchDTO(
                tag_id=1,
                tag_name="OpenAI",
                tag_type=TagType.COMPANY,
                confidence=0.9,
                matched_text="OpenAI",
                match_source="rule",
            ),
        ]

        item_tags = service.to_item_tags(item_id=100, tags=matches)

        assert len(item_tags) == 1
        assert item_tags[0].item_id == 100
        assert item_tags[0].tag_name == "OpenAI"
        assert item_tags[0].tag_type == TagType.COMPANY

    def test_to_topic_tags(self):
        """Test converting matches to topic tags."""
        from app.contracts.dto.tag import TagMatchDTO, TagType

        service = TagService()
        matches = [
            TagMatchDTO(
                tag_id=1,
                tag_name="PyTorch",
                tag_type=TagType.FRAMEWORK,
                confidence=0.85,
                matched_text="PyTorch",
                match_source="rule",
            ),
        ]

        topic_tags = service.to_topic_tags(topic_id=50, tags=matches)

        assert len(topic_tags) == 1
        assert topic_tags[0].topic_id == 50
        assert topic_tags[0].tag_name == "PyTorch"
        assert topic_tags[0].tag_type == TagType.FRAMEWORK

    def test_min_persist_confidence(self):
        """Test minimum confidence for persistence."""
        config = TagServiceConfig(min_persist_confidence=0.8)
        service = TagService(config=config)

        result = service.tag_text("openai mentioned in passing")

        # All returned tags should meet minimum confidence
        assert all(t.confidence >= 0.8 for t in result.tags)

    def test_max_tags_per_item(self):
        """Test maximum tags per item limit."""
        config = TagServiceConfig(max_tags_per_item=3)
        service = TagService(config=config)

        # Text with many entities
        result = service.tag_text(
            "OpenAI Google Microsoft Meta PyTorch TensorFlow GPT-4 Claude"
        )

        assert len(result.tags) <= 3

    def test_error_handling(self):
        """Test error handling in tag service."""
        service = TagService()

        # Should handle None gracefully
        from datetime import datetime, timezone
        from app.contracts.dto.normalized_item import NormalizedItemDTO

        item = NormalizedItemDTO(
            id=1,
            raw_item_id=1,
            source_id=1,
            title="Test",
            clean_text=None,
            excerpt=None,
            published_at=datetime.now(timezone.utc),
        )

        result = service.tag_item(item)
        assert result.success  # Should not crash

    def test_to_tagging_result_dto(self):
        """Test converting to TaggingResultDTO."""
        service = TagService()
        result = service.tag_text("OpenAI GPT-4")

        dto = service.to_tagging_result_dto(result)

        assert dto.tags == result.tags
        assert dto.processing_time_ms == result.processing_time_ms


class TestTaggingIntegration:
    """Integration tests for tagging system."""

    def test_full_tagging_pipeline(self):
        """Test complete tagging pipeline."""
        from datetime import datetime, timezone
        from app.contracts.dto.normalized_item import NormalizedItemDTO
        from app.common.enums import ContentType, BoardType

        service = TagService()

        # Create a realistic item
        item = NormalizedItemDTO(
            id=1,
            raw_item_id=1,
            source_id=1,
            title="Anthropic's Claude 3 Opus outperforms GPT-4 on benchmarks",
            clean_text="""
            Anthropic has released Claude 3 Opus, their most capable model yet.
            The model shows significant improvements in reasoning and coding tasks.
            It uses a transformer architecture similar to other large language models.
            The release comes as competition in the LLM space intensifies.
            """,
            excerpt="Claude 3 Opus benchmark results",
            published_at=datetime.now(timezone.utc),
            content_type=ContentType.ARTICLE,
            board_type_candidate=BoardType.AI,
        )

        result = service.tag_item(item)

        assert result.success
        assert len(result.tags) > 0

        # Check for expected tags
        tag_names = [t.tag_name for t in result.tags]
        assert "Anthropic" in tag_names
        assert "Claude" in tag_names
        assert "GPT-4" in tag_names

        # Check tag types
        company_tags = [t for t in result.tags if t.tag_type == TagType.COMPANY]
        model_tags = [t for t in result.tags if t.tag_type == TagType.MODEL]

        assert len(company_tags) >= 1
        assert len(model_tags) >= 2

    def test_chinese_company_names(self):
        """Test tagging Chinese company names."""
        service = TagService()

        result = service.tag_text(
            "Baidu's ERNIE and Alibaba's Qwen compete with OpenAI"
        )

        tag_names = [t.tag_name for t in result.tags]
        assert "Baidu" in tag_names
        assert "Alibaba" in tag_names
        assert "OpenAI" in tag_names

    def test_framework_detection(self):
        """Test framework detection in technical content."""
        service = TagService()

        result = service.tag_text(
            "We built our RAG pipeline using LangChain and LlamaIndex, "
            "with PyTorch for the embedding model"
        )

        framework_tags = [t for t in result.tags if t.tag_type == TagType.FRAMEWORK]
        framework_names = [t.tag_name for t in framework_tags]

        assert "LangChain" in framework_names
        assert "LlamaIndex" in framework_names
        assert "PyTorch" in framework_names

    def test_task_detection(self):
        """Test task detection."""
        service = TagService()

        result = service.tag_text(
            "Fine-tuning LLMs for code generation and question answering tasks"
        )

        task_tags = [t for t in result.tags if t.tag_type == TagType.TASK]
        task_names = [t.tag_name for t in task_tags]

        assert "Fine-tuning" in task_names
        assert "Code Generation" in task_names
        assert "Question Answering" in task_names
