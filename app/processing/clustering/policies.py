"""Merge policies for topic clustering.

This module defines policies that determine merge behavior based on
scores and other criteria.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.bootstrap.logging import get_logger
from app.processing.clustering.merge_scorer import MergeScoreResult

logger = get_logger(__name__)


class MergeDecision(StrEnum):
    """Possible merge decisions."""

    MUST_CREATE = "must_create"  # Definitely create new topic
    LIKELY_MERGE = "likely_merge"  # Strong merge candidate
    UNCERTAIN = "uncertain"  # Needs review or more data
    DO_NOT_MERGE = "do_not_merge"  # Should not merge


@dataclass
class PolicyResult:
    """Result of policy evaluation."""

    decision: MergeDecision
    target_topic_id: int | None
    confidence: float
    reason: str


class MergePolicy:
    """Base merge policy.

    Policies determine the final merge decision based on scores
    and additional criteria.
    """

    def __init__(
        self,
        *,
        must_create_threshold: float = 0.2,
        likely_merge_threshold: float = 0.6,
        uncertain_threshold: float = 0.4,
        min_confidence: float = 0.5,
    ) -> None:
        """Initialize policy.

        Args:
            must_create_threshold: Below this, must create new topic.
            likely_merge_threshold: Above this, likely merge.
            uncertain_threshold: Between must_create and this is uncertain.
            min_confidence: Minimum confidence for merge decision.
        """
        self._must_create_threshold = must_create_threshold
        self._likely_merge_threshold = likely_merge_threshold
        self._uncertain_threshold = uncertain_threshold
        self._min_confidence = min_confidence

    def evaluate(
        self,
        results: list[MergeScoreResult],
    ) -> PolicyResult:
        """Evaluate merge results and return policy decision.

        Args:
            results: List of merge score results, sorted by score descending.

        Returns:
            PolicyResult with decision.
        """
        if not results:
            return PolicyResult(
                decision=MergeDecision.MUST_CREATE,
                target_topic_id=None,
                confidence=1.0,
                reason="No candidate topics found",
            )

        best = results[0]

        # Check score thresholds
        if best.total_score < self._must_create_threshold:
            return PolicyResult(
                decision=MergeDecision.MUST_CREATE,
                target_topic_id=None,
                confidence=1.0 - best.total_score,
                reason=f"Best score {best.total_score:.2f} below threshold",
            )

        if best.total_score >= self._likely_merge_threshold:
            if best.confidence >= self._min_confidence:
                return PolicyResult(
                    decision=MergeDecision.LIKELY_MERGE,
                    target_topic_id=best.topic_id,
                    confidence=best.confidence,
                    reason=f"High score {best.total_score:.2f} with confidence {best.confidence:.2f}",
                )
            else:
                return PolicyResult(
                    decision=MergeDecision.UNCERTAIN,
                    target_topic_id=best.topic_id,
                    confidence=best.confidence,
                    reason=f"High score but low confidence {best.confidence:.2f}",
                )

        if best.total_score >= self._uncertain_threshold:
            return PolicyResult(
                decision=MergeDecision.UNCERTAIN,
                target_topic_id=best.topic_id,
                confidence=best.confidence,
                reason=f"Score {best.total_score:.2f} in uncertain range",
            )

        return PolicyResult(
            decision=MergeDecision.DO_NOT_MERGE,
            target_topic_id=None,
            confidence=1.0 - best.total_score,
            reason=f"Score {best.total_score:.2f} below merge threshold",
        )


class StrictMergePolicy(MergePolicy):
    """Strict merge policy requiring high confidence.

    Use this when false positives (incorrect merges) are costly.
    """

    def __init__(self) -> None:
        super().__init__(
            must_create_threshold=0.3,
            likely_merge_threshold=0.75,
            uncertain_threshold=0.5,
            min_confidence=0.7,
        )


class RelaxedMergePolicy(MergePolicy):
    """Relaxed merge policy allowing more merges.

    Use this when false negatives (missed merges) are costly.
    """

    def __init__(self) -> None:
        super().__init__(
            must_create_threshold=0.15,
            likely_merge_threshold=0.45,
            uncertain_threshold=0.3,
            min_confidence=0.4,
        )


class AdaptiveMergePolicy(MergePolicy):
    """Adaptive merge policy that adjusts based on topic count.

    When there are many topics, be more aggressive about merging.
    When there are few topics, be more conservative.
    """

    def __init__(
        self,
        *,
        topic_count_threshold: int = 100,
    ) -> None:
        """Initialize adaptive policy.

        Args:
            topic_count_threshold: Topic count above which to be more aggressive.
        """
        super().__init__()
        self._topic_count_threshold = topic_count_threshold

    def evaluate_with_context(
        self,
        results: list[MergeScoreResult],
        *,
        current_topic_count: int,
    ) -> PolicyResult:
        """Evaluate with topic count context.

        Args:
            results: Merge score results.
            current_topic_count: Current number of topics.

        Returns:
            PolicyResult with decision.
        """
        # Adjust thresholds based on topic count
        if current_topic_count > self._topic_count_threshold:
            # More aggressive merging
            self._likely_merge_threshold = 0.5
            self._uncertain_threshold = 0.35
            self._min_confidence = 0.45
        else:
            # More conservative
            self._likely_merge_threshold = 0.65
            self._uncertain_threshold = 0.45
            self._min_confidence = 0.55

        return self.evaluate(results)


class MultiSignalPolicy(MergePolicy):
    """Policy that requires multiple strong signals for merge.

    Requires at least N component scores above threshold.
    """

    def __init__(
        self,
        *,
        min_strong_signals: int = 2,
        strong_signal_threshold: float = 0.5,
    ) -> None:
        """Initialize multi-signal policy.

        Args:
            min_strong_signals: Minimum number of strong signals required.
            strong_signal_threshold: Threshold for a signal to be "strong".
        """
        super().__init__()
        self._min_strong_signals = min_strong_signals
        self._strong_signal_threshold = strong_signal_threshold

    def evaluate(
        self,
        results: list[MergeScoreResult],
    ) -> PolicyResult:
        """Evaluate requiring multiple strong signals.

        Args:
            results: Merge score results.

        Returns:
            PolicyResult with decision.
        """
        if not results:
            return PolicyResult(
                decision=MergeDecision.MUST_CREATE,
                target_topic_id=None,
                confidence=1.0,
                reason="No candidate topics found",
            )

        best = results[0]

        # Count strong signals
        strong_signals = sum(
            1
            for score in best.component_scores.values()
            if score >= self._strong_signal_threshold
        )

        if strong_signals >= self._min_strong_signals:
            if best.total_score >= self._likely_merge_threshold:
                return PolicyResult(
                    decision=MergeDecision.LIKELY_MERGE,
                    target_topic_id=best.topic_id,
                    confidence=best.confidence,
                    reason=f"{strong_signals} strong signals, score {best.total_score:.2f}",
                )
            else:
                return PolicyResult(
                    decision=MergeDecision.UNCERTAIN,
                    target_topic_id=best.topic_id,
                    confidence=best.confidence * 0.8,
                    reason=f"{strong_signals} strong signals but moderate score",
                )

        # Not enough strong signals
        if best.total_score < self._must_create_threshold:
            return PolicyResult(
                decision=MergeDecision.MUST_CREATE,
                target_topic_id=None,
                confidence=1.0 - best.total_score,
                reason=f"Only {strong_signals} strong signals, low score",
            )

        return PolicyResult(
            decision=MergeDecision.DO_NOT_MERGE,
            target_topic_id=None,
            confidence=0.6,
            reason=f"Only {strong_signals} strong signals (need {self._min_strong_signals})",
        )


def get_policy(name: str = "default") -> MergePolicy:
    """Get a merge policy by name.

    Args:
        name: Policy name (default, strict, relaxed, multi_signal).

    Returns:
        MergePolicy instance.

    Raises:
        ValueError: If policy name is unknown.
    """
    policies = {
        "default": MergePolicy,
        "strict": StrictMergePolicy,
        "relaxed": RelaxedMergePolicy,
        "multi_signal": MultiSignalPolicy,
        "adaptive": AdaptiveMergePolicy,
    }

    if name not in policies:
        raise ValueError(f"Unknown policy: {name}. Available: {list(policies.keys())}")

    return policies[name]()
