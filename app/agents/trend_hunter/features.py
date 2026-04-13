"""Trend feature extraction.

Extracts features for trend detection from topic data.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TrendFeatures:
    """Extracted trend features for a topic."""

    topic_id: int

    # Growth metrics
    item_count_total: int = 0
    item_count_7d: int = 0
    item_count_30d: int = 0
    growth_rate_7d: float = 0.0
    growth_rate_30d: float = 0.0

    # Source diversity
    source_count_total: int = 0
    source_count_7d: int = 0
    source_count_30d: int = 0
    source_diversity_score: float = 0.0
    unique_source_types: int = 0

    # Recency intensity
    items_last_24h: int = 0
    items_last_7d: int = 0
    recency_intensity: float = 0.0
    last_item_at: datetime | None = None

    # Activity patterns
    activity_consistency: float = 0.0  # How consistent is activity over time
    burst_score: float = 0.0  # Sudden spike detection
    momentum_score: float = 0.0  # Acceleration of activity

    # Related signals
    has_recent_release: bool = False
    has_discussion_spike: bool = False
    has_github_activity: bool = False
    related_entity_activity: list[str] = field(default_factory=list)

    # Repeated appearance
    appearance_count: int = 0  # How many times topic appeared
    repeated_appearance_score: float = 0.0

    # Historical context
    first_seen_at: datetime | None = None
    days_since_first_seen: int = 0
    historical_status: str | None = None

    # Computed scores
    overall_trend_score: float = 0.0
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "topic_id": self.topic_id,
            "item_count_total": self.item_count_total,
            "item_count_7d": self.item_count_7d,
            "item_count_30d": self.item_count_30d,
            "growth_rate_7d": self.growth_rate_7d,
            "growth_rate_30d": self.growth_rate_30d,
            "source_count_total": self.source_count_total,
            "source_count_7d": self.source_count_7d,
            "source_count_30d": self.source_count_30d,
            "source_diversity_score": self.source_diversity_score,
            "unique_source_types": self.unique_source_types,
            "items_last_24h": self.items_last_24h,
            "items_last_7d": self.items_last_7d,
            "recency_intensity": self.recency_intensity,
            "last_item_at": self.last_item_at.isoformat() if self.last_item_at else None,
            "activity_consistency": self.activity_consistency,
            "burst_score": self.burst_score,
            "momentum_score": self.momentum_score,
            "has_recent_release": self.has_recent_release,
            "has_discussion_spike": self.has_discussion_spike,
            "has_github_activity": self.has_github_activity,
            "related_entity_activity": self.related_entity_activity,
            "appearance_count": self.appearance_count,
            "repeated_appearance_score": self.repeated_appearance_score,
            "first_seen_at": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "days_since_first_seen": self.days_since_first_seen,
            "historical_status": self.historical_status,
            "overall_trend_score": self.overall_trend_score,
            "confidence": self.confidence,
        }


class TrendFeatureExtractor:
    """Extracts trend features from topic data."""

    def __init__(self) -> None:
        """Initialize the extractor."""
        self._now = datetime.now(timezone.utc)

    def extract(
        self,
        topic_id: int,
        *,
        topic_data: dict[str, Any] | None = None,
        items: list[dict[str, Any]] | None = None,
        historian_output: dict[str, Any] | None = None,
    ) -> TrendFeatures:
        """Extract trend features for a topic.

        Args:
            topic_id: Topic ID.
            topic_data: Topic metadata.
            items: List of topic items with timestamps.
            historian_output: Historian output for historical context.

        Returns:
            Extracted TrendFeatures.
        """
        features = TrendFeatures(topic_id=topic_id)
        self._now = datetime.now(timezone.utc)

        if topic_data:
            self._extract_from_topic_data(features, topic_data)

        if items:
            self._extract_from_items(features, items)

        if historian_output:
            self._extract_from_historian(features, historian_output)

        # Compute derived scores
        self._compute_derived_scores(features)

        return features

    def _extract_from_topic_data(
        self,
        features: TrendFeatures,
        topic_data: dict[str, Any],
    ) -> None:
        """Extract features from topic metadata."""
        features.item_count_total = topic_data.get("item_count", 0)
        features.source_count_total = topic_data.get("source_count", 0)

        first_seen = topic_data.get("first_seen_at")
        if first_seen:
            if isinstance(first_seen, str):
                first_seen = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
            features.first_seen_at = first_seen
            features.days_since_first_seen = (self._now - first_seen).days

        last_seen = topic_data.get("last_seen_at")
        if last_seen:
            if isinstance(last_seen, str):
                last_seen = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
            features.last_item_at = last_seen

    def _extract_from_items(
        self,
        features: TrendFeatures,
        items: list[dict[str, Any]],
    ) -> None:
        """Extract features from topic items."""
        if not items:
            return

        now = self._now
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        items_24h = 0
        items_7d = 0
        items_30d = 0
        sources_7d = set()
        sources_30d = set()
        source_types = set()

        # Daily activity for consistency calculation
        daily_counts: dict[str, int] = {}

        for item in items:
            published_at = item.get("published_at")
            if published_at:
                if isinstance(published_at, str):
                    published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))

                if published_at >= day_ago:
                    items_24h += 1
                if published_at >= week_ago:
                    items_7d += 1
                    source_id = item.get("source_id")
                    if source_id:
                        sources_7d.add(source_id)
                if published_at >= month_ago:
                    items_30d += 1
                    source_id = item.get("source_id")
                    if source_id:
                        sources_30d.add(source_id)

                # Track daily activity
                day_key = published_at.strftime("%Y-%m-%d")
                daily_counts[day_key] = daily_counts.get(day_key, 0) + 1

            # Track source types
            source_type = item.get("source_type")
            if source_type:
                source_types.add(source_type)

            # Check for release signals
            content_type = item.get("content_type", "")
            if content_type in ("release", "announcement", "launch"):
                features.has_recent_release = True

            # Check for discussion signals
            if content_type in ("discussion", "forum", "comment"):
                features.has_discussion_spike = True

            # Check for GitHub activity
            source_name = item.get("source_name", "").lower()
            if "github" in source_name:
                features.has_github_activity = True

        features.items_last_24h = items_24h
        features.items_last_7d = items_7d
        features.item_count_7d = items_7d
        features.item_count_30d = items_30d
        features.source_count_7d = len(sources_7d)
        features.source_count_30d = len(sources_30d)
        features.unique_source_types = len(source_types)

        # Calculate growth rates
        if items_30d > 0:
            # Growth rate: (recent - older) / older
            older_items = items_30d - items_7d
            if older_items > 0:
                features.growth_rate_7d = (items_7d - older_items / 3) / (older_items / 3 + 1)
            else:
                features.growth_rate_7d = items_7d  # All items are recent

        # Calculate activity consistency
        if daily_counts:
            counts = list(daily_counts.values())
            mean_count = sum(counts) / len(counts)
            if mean_count > 0:
                variance = sum((c - mean_count) ** 2 for c in counts) / len(counts)
                std_dev = variance ** 0.5
                # Coefficient of variation (lower = more consistent)
                cv = std_dev / mean_count if mean_count > 0 else 0
                features.activity_consistency = max(0, 1 - cv)

        # Calculate burst score (sudden spike)
        if items_7d > 0 and items_30d > 0:
            expected_weekly = items_30d / 4
            if expected_weekly > 0:
                features.burst_score = min(1.0, (items_7d - expected_weekly) / expected_weekly)

    def _extract_from_historian(
        self,
        features: TrendFeatures,
        historian_output: dict[str, Any],
    ) -> None:
        """Extract features from historian output."""
        features.historical_status = historian_output.get("historical_status")

        first_seen = historian_output.get("first_seen_at")
        if first_seen and not features.first_seen_at:
            if isinstance(first_seen, str):
                first_seen = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
            features.first_seen_at = first_seen
            features.days_since_first_seen = (self._now - first_seen).days

        # Count appearances from timeline
        timeline = historian_output.get("timeline_points", [])
        features.appearance_count = len(timeline)

        # Calculate repeated appearance score
        if features.appearance_count > 1:
            # More appearances = higher score, but with diminishing returns
            features.repeated_appearance_score = min(1.0, features.appearance_count / 10)

    def _compute_derived_scores(self, features: TrendFeatures) -> None:
        """Compute derived trend scores."""
        # Recency intensity: how active is the topic recently
        if features.item_count_total > 0:
            features.recency_intensity = features.items_last_7d / features.item_count_total
        else:
            features.recency_intensity = 0.0

        # Source diversity score
        if features.source_count_total > 0:
            # Normalize by total sources
            diversity = features.source_count_7d / features.source_count_total
            # Bonus for multiple source types
            type_bonus = min(0.2, features.unique_source_types * 0.05)
            features.source_diversity_score = min(1.0, diversity + type_bonus)

        # Momentum score: acceleration of activity
        if features.growth_rate_7d > 0:
            features.momentum_score = min(1.0, features.growth_rate_7d * 0.5)

        # Overall trend score
        features.overall_trend_score = self._compute_overall_score(features)

        # Confidence based on data availability
        features.confidence = self._compute_confidence(features)

    def _compute_overall_score(self, features: TrendFeatures) -> float:
        """Compute overall trend score."""
        score = 0.0

        # Growth component (30%)
        growth_score = min(1.0, max(0, features.growth_rate_7d))
        score += growth_score * 0.30

        # Recency component (25%)
        score += features.recency_intensity * 0.25

        # Source diversity component (15%)
        score += features.source_diversity_score * 0.15

        # Momentum component (15%)
        score += features.momentum_score * 0.15

        # Signal bonuses (15%)
        signal_score = 0.0
        if features.has_recent_release:
            signal_score += 0.4
        if features.has_discussion_spike:
            signal_score += 0.3
        if features.has_github_activity:
            signal_score += 0.3
        score += min(1.0, signal_score) * 0.15

        return min(1.0, score)

    def _compute_confidence(self, features: TrendFeatures) -> float:
        """Compute confidence in the trend assessment."""
        confidence = 0.5  # Base confidence

        # More items = higher confidence
        if features.item_count_total >= 10:
            confidence += 0.2
        elif features.item_count_total >= 5:
            confidence += 0.1

        # More sources = higher confidence
        if features.source_count_total >= 5:
            confidence += 0.15
        elif features.source_count_total >= 3:
            confidence += 0.1

        # Historical context = higher confidence
        if features.historical_status:
            confidence += 0.1

        # Recent activity = higher confidence
        if features.items_last_7d >= 3:
            confidence += 0.05

        return min(1.0, confidence)


def extract_trend_features(
    topic_id: int,
    *,
    topic_data: dict[str, Any] | None = None,
    items: list[dict[str, Any]] | None = None,
    historian_output: dict[str, Any] | None = None,
) -> TrendFeatures:
    """Convenience function to extract trend features.

    Args:
        topic_id: Topic ID.
        topic_data: Topic metadata.
        items: List of topic items.
        historian_output: Historian output.

    Returns:
        Extracted TrendFeatures.
    """
    extractor = TrendFeatureExtractor()
    return extractor.extract(
        topic_id,
        topic_data=topic_data,
        items=items,
        historian_output=historian_output,
    )
