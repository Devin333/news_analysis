"""Search policies for different search modes."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SearchPolicyMode(StrEnum):
    """Search policy modes for different use cases."""

    USER_SEARCH = "user_search"
    TOPIC_LOOKUP = "topic_lookup"
    ENTITY_LOOKUP = "entity_lookup"
    HISTORICAL_CASE_LOOKUP = "historical_case_lookup"
    AGENT_RETRIEVAL = "agent_retrieval"
    SIMILAR_CONTENT = "similar_content"


class SearchPolicyConfig(BaseModel):
    """Configuration for a search policy."""

    mode: SearchPolicyMode
    keyword_enabled: bool = True
    semantic_enabled: bool = True
    keyword_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    semantic_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)
    boost_hybrid: bool = True
    hybrid_boost_factor: float = Field(default=1.2, ge=1.0)
    merge_strategy: str = "weighted"  # weighted, rrf, interleaved
    max_results: int = Field(default=20, ge=1, le=100)
    include_explanation: bool = False


class SearchPolicies:
    """Search policies for different use cases.

    Provides pre-configured policies for common search scenarios.
    """

    @staticmethod
    def user_search() -> SearchPolicyConfig:
        """Policy for user-facing search.

        Balanced keyword and semantic search with good UX.
        """
        return SearchPolicyConfig(
            mode=SearchPolicyMode.USER_SEARCH,
            keyword_enabled=True,
            semantic_enabled=True,
            keyword_weight=0.5,
            semantic_weight=0.5,
            min_score=0.1,
            boost_hybrid=True,
            hybrid_boost_factor=1.2,
            merge_strategy="weighted",
            max_results=20,
            include_explanation=False,
        )

    @staticmethod
    def topic_lookup() -> SearchPolicyConfig:
        """Policy for topic lookup.

        Prioritizes exact matches and keyword search.
        """
        return SearchPolicyConfig(
            mode=SearchPolicyMode.TOPIC_LOOKUP,
            keyword_enabled=True,
            semantic_enabled=True,
            keyword_weight=0.7,
            semantic_weight=0.3,
            min_score=0.2,
            boost_hybrid=True,
            hybrid_boost_factor=1.1,
            merge_strategy="weighted",
            max_results=10,
            include_explanation=False,
        )

    @staticmethod
    def entity_lookup() -> SearchPolicyConfig:
        """Policy for entity lookup.

        Prioritizes exact name matches.
        """
        return SearchPolicyConfig(
            mode=SearchPolicyMode.ENTITY_LOOKUP,
            keyword_enabled=True,
            semantic_enabled=False,
            keyword_weight=1.0,
            semantic_weight=0.0,
            min_score=0.3,
            boost_hybrid=False,
            merge_strategy="weighted",
            max_results=10,
            include_explanation=False,
        )

    @staticmethod
    def historical_case_lookup() -> SearchPolicyConfig:
        """Policy for historical case lookup.

        Prioritizes semantic similarity for finding related cases.
        """
        return SearchPolicyConfig(
            mode=SearchPolicyMode.HISTORICAL_CASE_LOOKUP,
            keyword_enabled=True,
            semantic_enabled=True,
            keyword_weight=0.3,
            semantic_weight=0.7,
            min_score=0.4,
            boost_hybrid=True,
            hybrid_boost_factor=1.3,
            merge_strategy="rrf",
            max_results=15,
            include_explanation=True,
        )

    @staticmethod
    def agent_retrieval() -> SearchPolicyConfig:
        """Policy for agent internal retrieval.

        High recall, semantic-focused for context gathering.
        """
        return SearchPolicyConfig(
            mode=SearchPolicyMode.AGENT_RETRIEVAL,
            keyword_enabled=True,
            semantic_enabled=True,
            keyword_weight=0.4,
            semantic_weight=0.6,
            min_score=0.2,
            boost_hybrid=True,
            hybrid_boost_factor=1.2,
            merge_strategy="rrf",
            max_results=30,
            include_explanation=False,
        )

    @staticmethod
    def similar_content() -> SearchPolicyConfig:
        """Policy for finding similar content.

        Pure semantic search for similarity.
        """
        return SearchPolicyConfig(
            mode=SearchPolicyMode.SIMILAR_CONTENT,
            keyword_enabled=False,
            semantic_enabled=True,
            keyword_weight=0.0,
            semantic_weight=1.0,
            min_score=0.5,
            boost_hybrid=False,
            merge_strategy="weighted",
            max_results=10,
            include_explanation=False,
        )

    @staticmethod
    def get_policy(mode: SearchPolicyMode) -> SearchPolicyConfig:
        """Get policy by mode.

        Args:
            mode: Policy mode

        Returns:
            SearchPolicyConfig for the mode
        """
        policies = {
            SearchPolicyMode.USER_SEARCH: SearchPolicies.user_search,
            SearchPolicyMode.TOPIC_LOOKUP: SearchPolicies.topic_lookup,
            SearchPolicyMode.ENTITY_LOOKUP: SearchPolicies.entity_lookup,
            SearchPolicyMode.HISTORICAL_CASE_LOOKUP: SearchPolicies.historical_case_lookup,
            SearchPolicyMode.AGENT_RETRIEVAL: SearchPolicies.agent_retrieval,
            SearchPolicyMode.SIMILAR_CONTENT: SearchPolicies.similar_content,
        }

        factory = policies.get(mode, SearchPolicies.user_search)
        return factory()

    @staticmethod
    def customize(
        base_mode: SearchPolicyMode,
        **overrides: Any,
    ) -> SearchPolicyConfig:
        """Create customized policy from base.

        Args:
            base_mode: Base policy mode
            **overrides: Fields to override

        Returns:
            Customized SearchPolicyConfig
        """
        base = SearchPolicies.get_policy(base_mode)
        return base.model_copy(update=overrides)
