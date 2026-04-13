"""Subscription matching policies."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MatchPolicyType(StrEnum):
    """Match policy types."""

    STRICT = "strict"
    FUZZY = "fuzzy"
    SEMANTIC = "semantic"


class MatchPolicyConfig(BaseModel):
    """Configuration for a match policy."""

    policy_type: MatchPolicyType
    min_score: float = Field(default=0.5, ge=0.0, le=1.0)
    require_all_tags: bool = False
    case_sensitive: bool = False
    partial_match: bool = True
    semantic_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class SubscriptionMatchPolicies:
    """Match policies for different subscription types."""

    @staticmethod
    def strict() -> MatchPolicyConfig:
        """Strict matching policy.

        Requires exact matches.
        """
        return MatchPolicyConfig(
            policy_type=MatchPolicyType.STRICT,
            min_score=0.8,
            require_all_tags=True,
            case_sensitive=False,
            partial_match=False,
        )

    @staticmethod
    def fuzzy() -> MatchPolicyConfig:
        """Fuzzy matching policy.

        Allows partial and approximate matches.
        """
        return MatchPolicyConfig(
            policy_type=MatchPolicyType.FUZZY,
            min_score=0.5,
            require_all_tags=False,
            case_sensitive=False,
            partial_match=True,
        )

    @staticmethod
    def semantic() -> MatchPolicyConfig:
        """Semantic matching policy.

        Uses semantic similarity for matching.
        """
        return MatchPolicyConfig(
            policy_type=MatchPolicyType.SEMANTIC,
            min_score=0.6,
            require_all_tags=False,
            case_sensitive=False,
            partial_match=True,
            semantic_threshold=0.7,
        )

    @staticmethod
    def for_subscription_type(subscription_type: str) -> MatchPolicyConfig:
        """Get policy for subscription type.

        Args:
            subscription_type: Type of subscription.

        Returns:
            Appropriate MatchPolicyConfig.
        """
        policies = {
            "query": SubscriptionMatchPolicies.fuzzy(),
            "tag": SubscriptionMatchPolicies.strict(),
            "entity": SubscriptionMatchPolicies.strict(),
            "topic": SubscriptionMatchPolicies.strict(),
            "board": SubscriptionMatchPolicies.strict(),
        }
        return policies.get(subscription_type, SubscriptionMatchPolicies.fuzzy())
