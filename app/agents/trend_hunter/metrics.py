"""Trend metrics calculation.

Provides unified trend metric computation for topics.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any

from app.agents.trend_hunter.features import TrendFeatures, extract_trend_features
from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


class TrendStageLabel(StrEnum):
    """Labels for trend stages."""

    EMERGING = "emerging"
    RISING = "rising"
    PEAK = "peak"
    STABLE = "stable"
    DECLINING = "declining"
    DORMANT = "dormant"


class TrendSignalType(StrEnum):
    """Types of trend signals."""

    GROWTH = "growth"
    DIVERSITY = "diversity"
    RECENCY = "recency"
    RELEASE = "release"
    DISCUSSION = "discussion"
    GITHUB = "github"
    REPEATED = "repeated"
    BURST = "burst"


@dataclass
class TrendSignalResult:
    """Result of a trend signal detection."""

    signal_type: str
    strength: float  # 0-1
    description: str
    evidence: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_type": self.signal_type,
            "strength": self.strength,
            "description": self.description,
            "evidence": self.evidence,
        }


@dataclass
class TrendMetrics:
    """Computed trend metrics for a topic."""

    topic_id: int
    trend_score: float
    stage: TrendStageLabel
    signals: list[TrendSignalResult]
    is_emerging: bool
    recommended_for_homepage: bool
    confidence: float
    computed_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic_id": self.topic_id,
            "trend_score": self.trend_score,
            "stage": self.stage.value,
            "signals": [s.to_dict() for s in self.signals],
            "is_emerging": self.is_emerging,
            "recommended_for_homepage": self.recommended_for_homepage,
            "confidence": self.confidence,
            "computed_at": self.computed_at.isoformat(),
        }


class TrendMetricsCalculator:
    """Calculates trend metrics from features."""

    # Thresholds for trend detection
    EMERGING_THRESHOLD = 0.6
    RISING_THRESHOLD = 0.7
    PEAK_THRESHOLD = 0.85
    HOMEPAGE_THRESHOLD = 0.75

    def __init__(self) -> None:
        """Initialize the calculator."""
        pass

    def calculate(self, features: TrendFeatures) -> TrendMetrics:
        """Calculate trend metrics from features.

        Args:
            features: Extracted trend features.

        Returns:
            Computed TrendMetrics.
        """
        # Detect signals
        signals = self._detect_signals(features)

        # Calculate overall trend score
        trend_score = self._calculate_trend_score(features, signals)

        # Determine stage
        stage = self._determine_stage(features, trend_score)

        # Determine if emerging
        is_emerging = self._is_emerging(features, trend_score, stage)

        # Determine homepage recommendation
        recommended = self._should_recommend_homepage(features, trend_score, signals)

        return TrendMetrics(
            topic_id=features.topic_id,
            trend_score=trend_score,
            stage=stage,
            signals=signals,
            is_emerging=is_emerging,
            recommended_for_homepage=recommended,
            confidence=features.confidence,
            computed_at=datetime.now(timezone.utc),
        )

    def _detect_signals(self, features: TrendFeatures) -> list[TrendSignalResult]:
        """Detect trend signals from features."""
        signals = []

        # Growth signal
        if features.growth_rate_7d > 0.2:
            strength = min(1.0, features.growth_rate_7d)
            signals.append(TrendSignalResult(
                signal_type=TrendSignalType.GROWTH,
                strength=strength,
                description=f"Growth rate of {features.growth_rate_7d:.1%} in last 7 days",
                evidence=[
                    f"{features.item_count_7d} items in last 7 days",
                    f"{features.item_count_30d} items in last 30 days",
                ],
            ))

        # Source diversity signal
        if features.source_diversity_score > 0.4:
            signals.append(TrendSignalResult(
                signal_type=TrendSignalType.DIVERSITY,
                strength=features.source_diversity_score,
                description=f"High source diversity ({features.source_count_7d} sources)",
                evidence=[
                    f"{features.unique_source_types} different source types",
                    f"{features.source_count_7d} sources in last 7 days",
                ],
            ))

        # Recency signal
        if features.recency_intensity > 0.5:
            signals.append(TrendSignalResult(
                signal_type=TrendSignalType.RECENCY,
                strength=features.recency_intensity,
                description="High recent activity",
                evidence=[
                    f"{features.items_last_24h} items in last 24 hours",
                    f"{features.items_last_7d} items in last 7 days",
                ],
            ))

        # Release signal
        if features.has_recent_release:
            signals.append(TrendSignalResult(
                signal_type=TrendSignalType.RELEASE,
                strength=0.8,
                description="Recent release or announcement detected",
                evidence=["Release/announcement content found"],
            ))

        # Discussion signal
        if features.has_discussion_spike:
            signals.append(TrendSignalResult(
                signal_type=TrendSignalType.DISCUSSION,
                strength=0.6,
                description="Discussion activity detected",
                evidence=["Discussion/forum content found"],
            ))

        # GitHub signal
        if features.has_github_activity:
            signals.append(TrendSignalResult(
                signal_type=TrendSignalType.GITHUB,
                strength=0.7,
                description="GitHub activity detected",
                evidence=["GitHub-related content found"],
            ))

        # Repeated appearance signal
        if features.repeated_appearance_score > 0.3:
            signals.append(TrendSignalResult(
                signal_type=TrendSignalType.REPEATED,
                strength=features.repeated_appearance_score,
                description=f"Topic has appeared {features.appearance_count} times",
                evidence=[f"{features.appearance_count} historical appearances"],
            ))

        # Burst signal
        if features.burst_score > 0.3:
            signals.append(TrendSignalResult(
                signal_type=TrendSignalType.BURST,
                strength=features.burst_score,
                description="Sudden activity spike detected",
                evidence=[f"Burst score: {features.burst_score:.2f}"],
            ))

        return signals

    def _calculate_trend_score(
        self,
        features: TrendFeatures,
        signals: list[TrendSignalResult],
    ) -> float:
        """Calculate overall trend score."""
        # Base score from features
        base_score = features.overall_trend_score

        # Signal boost
        if signals:
            signal_boost = sum(s.strength for s in signals) / len(signals) * 0.2
            base_score = min(1.0, base_score + signal_boost)

        return base_score

    def _determine_stage(
        self,
        features: TrendFeatures,
        trend_score: float,
    ) -> TrendStageLabel:
        """Determine the trend stage."""
        # Check for dormant
        if features.items_last_7d == 0:
            return TrendStageLabel.DORMANT

        # Check historical status
        historical = features.historical_status
        if historical == "new":
            if trend_score >= self.EMERGING_THRESHOLD:
                return TrendStageLabel.EMERGING
            return TrendStageLabel.STABLE

        # Score-based determination
        if trend_score >= self.PEAK_THRESHOLD:
            return TrendStageLabel.PEAK
        elif trend_score >= self.RISING_THRESHOLD:
            return TrendStageLabel.RISING
        elif trend_score >= self.EMERGING_THRESHOLD:
            return TrendStageLabel.EMERGING

        # Check for declining
        if features.growth_rate_7d < -0.2:
            return TrendStageLabel.DECLINING

        return TrendStageLabel.STABLE

    def _is_emerging(
        self,
        features: TrendFeatures,
        trend_score: float,
        stage: TrendStageLabel,
    ) -> bool:
        """Determine if topic is an emerging trend."""
        # Must have recent activity
        if features.items_last_7d < 2:
            return False

        # Check stage
        if stage in (TrendStageLabel.EMERGING, TrendStageLabel.RISING):
            return True

        # Check for new topics with good score
        if features.historical_status == "new" and trend_score >= 0.5:
            return True

        # Check for growth
        if features.growth_rate_7d > 0.5 and trend_score >= 0.5:
            return True

        return False

    def _should_recommend_homepage(
        self,
        features: TrendFeatures,
        trend_score: float,
        signals: list[TrendSignalResult],
    ) -> bool:
        """Determine if topic should be featured on homepage."""
        # Must meet threshold
        if trend_score < self.HOMEPAGE_THRESHOLD:
            return False

        # Must have multiple signals
        if len(signals) < 2:
            return False

        # Must have recent activity
        if features.items_last_24h < 1:
            return False

        # Must have source diversity
        if features.source_count_7d < 2:
            return False

        return True


def calculate_trend_metrics(
    topic_id: int,
    *,
    topic_data: dict[str, Any] | None = None,
    items: list[dict[str, Any]] | None = None,
    historian_output: dict[str, Any] | None = None,
) -> TrendMetrics:
    """Convenience function to calculate trend metrics.

    Args:
        topic_id: Topic ID.
        topic_data: Topic metadata.
        items: List of topic items.
        historian_output: Historian output.

    Returns:
        Computed TrendMetrics.
    """
    # Extract features
    features = extract_trend_features(
        topic_id,
        topic_data=topic_data,
        items=items,
        historian_output=historian_output,
    )

    # Calculate metrics
    calculator = TrendMetricsCalculator()
    return calculator.calculate(features)


def batch_calculate_metrics(
    topics: list[dict[str, Any]],
) -> list[TrendMetrics]:
    """Calculate metrics for multiple topics.

    Args:
        topics: List of topic dicts with 'id', 'data', 'items', 'historian'.

    Returns:
        List of TrendMetrics.
    """
    results = []
    calculator = TrendMetricsCalculator()

    for topic in topics:
        topic_id = topic.get("id")
        if topic_id is None:
            continue

        features = extract_trend_features(
            topic_id,
            topic_data=topic.get("data"),
            items=topic.get("items"),
            historian_output=topic.get("historian"),
        )
        metrics = calculator.calculate(features)
        results.append(metrics)

    return results
