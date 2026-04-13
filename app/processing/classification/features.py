"""Classification features extraction.

This module provides feature extraction for content classification,
including source type, title keywords, tags, and content type features.
"""

from dataclasses import dataclass, field
from typing import Any

from app.bootstrap.logging import get_logger
from app.common.enums import BoardType, ContentType, SourceType

logger = get_logger(__name__)


# Keywords that indicate AI/tech content
AI_KEYWORDS = {
    "ai", "artificial intelligence", "machine learning", "ml", "deep learning",
    "neural network", "llm", "large language model", "gpt", "chatgpt", "claude",
    "gemini", "transformer", "nlp", "natural language", "computer vision",
    "reinforcement learning", "generative ai", "gen ai", "diffusion",
    "stable diffusion", "midjourney", "dall-e", "openai", "anthropic",
    "google ai", "meta ai", "hugging face", "pytorch", "tensorflow",
    "langchain", "llamaindex", "rag", "retrieval augmented", "fine-tuning",
    "embedding", "vector database", "prompt engineering", "agent", "multimodal",
}

# Keywords that indicate news content
NEWS_KEYWORDS = {
    "announces", "announced", "launches", "launched", "releases", "released",
    "unveils", "unveiled", "introduces", "introduced", "reports", "reported",
    "breaking", "exclusive", "update", "news", "today", "yesterday",
    "acquisition", "acquired", "funding", "raised", "valuation", "ipo",
    "partnership", "collaboration", "deal", "merger",
}

# Keywords that indicate research/academic content
RESEARCH_KEYWORDS = {
    "paper", "research", "study", "findings", "experiment", "benchmark",
    "evaluation", "dataset", "arxiv", "preprint", "journal", "conference",
    "icml", "neurips", "iclr", "cvpr", "acl", "emnlp", "aaai",
    "methodology", "hypothesis", "results", "conclusion", "abstract",
}

# Keywords that indicate engineering/technical content
ENGINEERING_KEYWORDS = {
    "tutorial", "guide", "how to", "implementation", "code", "github",
    "repository", "library", "framework", "api", "sdk", "documentation",
    "deploy", "deployment", "production", "infrastructure", "scaling",
    "optimization", "performance", "debugging", "testing", "ci/cd",
}


@dataclass
class ClassificationFeatures:
    """Features extracted for classification."""

    # Source features
    source_type: SourceType | None = None
    source_trust_score: float = 0.5

    # Title features
    title_keywords: set[str] = field(default_factory=set)
    title_ai_score: float = 0.0
    title_news_score: float = 0.0
    title_research_score: float = 0.0
    title_engineering_score: float = 0.0

    # Content features
    content_type: ContentType | None = None
    content_length: int = 0

    # Tag features
    tags: list[str] = field(default_factory=list)
    tag_types: dict[str, int] = field(default_factory=dict)

    # Derived scores
    ai_relevance: float = 0.0
    news_relevance: float = 0.0
    research_relevance: float = 0.0
    engineering_relevance: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_type": self.source_type.value if self.source_type else None,
            "source_trust_score": self.source_trust_score,
            "title_ai_score": self.title_ai_score,
            "title_news_score": self.title_news_score,
            "title_research_score": self.title_research_score,
            "title_engineering_score": self.title_engineering_score,
            "content_type": self.content_type.value if self.content_type else None,
            "content_length": self.content_length,
            "tag_count": len(self.tags),
            "ai_relevance": self.ai_relevance,
            "news_relevance": self.news_relevance,
            "research_relevance": self.research_relevance,
            "engineering_relevance": self.engineering_relevance,
        }


def _compute_keyword_score(text: str, keywords: set[str]) -> float:
    """Compute keyword match score.

    Args:
        text: Text to analyze.
        keywords: Set of keywords to match.

    Returns:
        Score between 0 and 1.
    """
    if not text:
        return 0.0

    text_lower = text.lower()
    matches = sum(1 for kw in keywords if kw in text_lower)

    # Normalize by keyword set size, cap at 1.0
    if matches == 0:
        return 0.0

    # Use diminishing returns formula
    score = min(matches / 3.0, 1.0)
    return score


def extract_features(
    *,
    title: str = "",
    clean_text: str = "",
    excerpt: str = "",
    source_type: SourceType | None = None,
    content_type: ContentType | None = None,
    tags: list[str] | None = None,
    source_trust_score: float = 0.5,
) -> ClassificationFeatures:
    """Extract classification features from content.

    Args:
        title: Content title.
        clean_text: Cleaned content text.
        excerpt: Content excerpt/summary.
        source_type: Type of source.
        content_type: Type of content.
        tags: List of tags.
        source_trust_score: Trust score of source.

    Returns:
        ClassificationFeatures with extracted features.
    """
    features = ClassificationFeatures(
        source_type=source_type,
        source_trust_score=source_trust_score,
        content_type=content_type,
        content_length=len(clean_text) if clean_text else 0,
        tags=tags or [],
    )

    # Extract title keywords
    if title:
        title_lower = title.lower()
        features.title_keywords = {
            word for word in title_lower.split()
            if len(word) > 2
        }

    # Compute title scores
    combined_text = f"{title} {excerpt}"
    features.title_ai_score = _compute_keyword_score(combined_text, AI_KEYWORDS)
    features.title_news_score = _compute_keyword_score(combined_text, NEWS_KEYWORDS)
    features.title_research_score = _compute_keyword_score(combined_text, RESEARCH_KEYWORDS)
    features.title_engineering_score = _compute_keyword_score(combined_text, ENGINEERING_KEYWORDS)

    # Count tag types
    if tags:
        for tag in tags:
            tag_lower = tag.lower()
            if any(kw in tag_lower for kw in AI_KEYWORDS):
                features.tag_types["ai"] = features.tag_types.get("ai", 0) + 1
            if any(kw in tag_lower for kw in NEWS_KEYWORDS):
                features.tag_types["news"] = features.tag_types.get("news", 0) + 1

    # Compute overall relevance scores
    features.ai_relevance = _compute_ai_relevance(features)
    features.news_relevance = _compute_news_relevance(features)
    features.research_relevance = _compute_research_relevance(features)
    features.engineering_relevance = _compute_engineering_relevance(features)

    return features


def _compute_ai_relevance(features: ClassificationFeatures) -> float:
    """Compute AI relevance score."""
    score = 0.0

    # Title AI keywords
    score += features.title_ai_score * 0.4

    # Source type bonus
    if features.source_type == SourceType.ARXIV:
        score += 0.3
    elif features.source_type == SourceType.GITHUB:
        score += 0.2

    # Content type bonus
    if features.content_type == ContentType.PAPER:
        score += 0.2
    elif features.content_type == ContentType.REPOSITORY:
        score += 0.15

    # Tag bonus
    ai_tag_count = features.tag_types.get("ai", 0)
    score += min(ai_tag_count * 0.1, 0.3)

    return min(score, 1.0)


def _compute_news_relevance(features: ClassificationFeatures) -> float:
    """Compute news relevance score."""
    score = 0.0

    # Title news keywords
    score += features.title_news_score * 0.5

    # Source type bonus
    if features.source_type == SourceType.RSS:
        score += 0.2
    elif features.source_type == SourceType.WEB:
        score += 0.1

    # Content type bonus
    if features.content_type == ContentType.ARTICLE:
        score += 0.2

    return min(score, 1.0)


def _compute_research_relevance(features: ClassificationFeatures) -> float:
    """Compute research relevance score."""
    score = 0.0

    # Title research keywords
    score += features.title_research_score * 0.4

    # Source type bonus
    if features.source_type == SourceType.ARXIV:
        score += 0.4

    # Content type bonus
    if features.content_type == ContentType.PAPER:
        score += 0.3

    return min(score, 1.0)


def _compute_engineering_relevance(features: ClassificationFeatures) -> float:
    """Compute engineering relevance score."""
    score = 0.0

    # Title engineering keywords
    score += features.title_engineering_score * 0.4

    # Source type bonus
    if features.source_type == SourceType.GITHUB:
        score += 0.3

    # Content type bonus
    if features.content_type == ContentType.REPOSITORY:
        score += 0.3

    return min(score, 1.0)
