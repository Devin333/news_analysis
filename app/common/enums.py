"""Global enums for domain and application."""

from enum import StrEnum


class Environment(StrEnum):
    """Application running environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class BoardType(StrEnum):
    """Topic board classification."""

    GENERAL = "general"
    AI = "ai"
    ENGINEERING = "engineering"
    RESEARCH = "research"


class SourceType(StrEnum):
    """Supported source types."""

    RSS = "rss"
    WEB = "web"
    GITHUB = "github"
    ARXIV = "arxiv"


class ContentType(StrEnum):
    """Normalized content type."""

    ARTICLE = "article"
    BLOG = "blog"
    PAPER = "paper"
    REPOSITORY = "repository"
    RELEASE = "release"
    CHANGELOG = "changelog"
    DISCUSSION = "discussion"
    THREAD = "thread"
    VIDEO = "video"
    PODCAST = "podcast"
