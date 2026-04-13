"""Tagging module for content classification."""

from app.processing.tagging.dictionaries import (
    COMPANY_ALIASES,
    FRAMEWORK_NAMES,
    MODEL_NAMES,
    TASK_KEYWORDS,
    DOMAIN_KEYWORDS,
)
from app.processing.tagging.rule_tagger import RuleTagger, get_rule_tagger
from app.processing.tagging.tag_service import TagService, get_tag_service
from app.processing.tagging.topic_tag_aggregator import (
    TopicTagAggregator,
    get_topic_tag_aggregator,
)

__all__ = [
    "COMPANY_ALIASES",
    "FRAMEWORK_NAMES",
    "MODEL_NAMES",
    "TASK_KEYWORDS",
    "DOMAIN_KEYWORDS",
    "RuleTagger",
    "get_rule_tagger",
    "TagService",
    "get_tag_service",
    "TopicTagAggregator",
    "get_topic_tag_aggregator",
]
