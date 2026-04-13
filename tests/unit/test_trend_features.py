"""Tests for Trend Hunter features and metrics."""

import pytest
from datetime import datetime, timedelta, timezone

from app.agents.trend_hunter.features import (
    TrendFeatures,
    TrendFeatureExtractor,
    extract_trend_features,
)
from app.agents.trend_hunter.metrics import (
    TrendStageLabel,
    TrendSignalType,
    TrendSignalResult,
    TrendMetrics,
    TrendMetricsCalculator,
    calculate_trend_metrics,
)


class TestTrendFeatures:
    """Tests for TrendFeatures dataclass."""

    def test_create_trend_features(self):
        """Test creating trend features."""
        features = TrendFeatures(topic_id=1)
        assert features.topic_id == 1
        assert features.item_count_total == 0
        assert features.growth_rate_7d == 0.0

    def test_trend_features_to_dict(self):
        """Test converting features to dict."""
        features = TrendFeatures(
            topic_id=1,
            item_count_total=10,
            growth_rate_7d=0.5,
        )
        data = features.to_dict()
        assert data["topic_id"] == 1
        assert data["item_count_total"] == 10
        assert data["growth_rate_7d"] == 0.5


class TestTrendFeatureExtractor:
    """Tests for TrendFeatureExtractor."""

    def test_extract_from_topic_data(self):
        """Test extracting features from topic data."""
        extractor = TrendFeatureExtractor()
        features = extractor.extract(
            topic_id=1,
            topic_data={
                "item_count": 10,
                "source_count": 5,
                "first_seen_at": datetime.now(timezone.utc) - timedelta(days=30),
            },
        )
        assert features.item_count_total == 10
        assert features.source_count_total == 5
        assert features.days_since_first_seen >= 29

    def test_extract_from_items(self):
        """Test extracting features from items."""
        now = datetime.now(timezone.utc)
        items = [
            {"published_at": now - timedelta(hours=12), "source_id": 1},
            {"published_at": now - timedelta(days=2), "source_id": 2},
            {"published_at": now - timedelta(days=5), "source_id": 3},
            {"published_at": now - timedelta(days=10), "source_id": 1},
        ]
        
        extractor = TrendFeatureExtractor()
        features = extractor.extract(topic_id=1, items=items)
        
        assert features.items_last_24h == 1
        assert features.items_last_7d == 3
        assert features.item_count_7d == 3

    def test_extract_with_historian_output(self):
        """Test extracting features with historian output."""
        extractor = TrendFeatureExtractor()
        features = extractor.extract(
            topic_id=1,
            historian_output={
                "historical_status": "evolving",
                "first_seen_at": datetime.now(timezone.utc) - timedelta(days=60),
                "timeline_points": [
                    {"event_time": datetime.now(timezone.utc) - timedelta(days=30)},
                    {"event_time": datetime.now(timezone.utc) - timedelta(days=15)},
                ],
            },
        )
        assert features.historical_status == "evolving"
        assert features.appearance_count == 2
        assert features.repeated_appearance_score > 0


class TestTrendMetricsCalculator:
    """Tests for TrendMetricsCalculator."""

    def test_calculate_metrics_stable(self):
        """Test calculating metrics for stable topic."""
        features = TrendFeatures(
            topic_id=1,
            item_count_total=10,
            items_last_7d=2,
            growth_rate_7d=0.1,
        )
        
        calculator = TrendMetricsCalculator()
        metrics = calculator.calculate(features)
        
        assert metrics.topic_id == 1
        assert metrics.stage == TrendStageLabel.STABLE
        assert not metrics.is_emerging

    def test_calculate_metrics_emerging(self):
        """Test calculating metrics for emerging topic."""
        features = TrendFeatures(
            topic_id=1,
            item_count_total=15,
            items_last_7d=10,
            items_last_24h=3,
            growth_rate_7d=0.8,
            source_count_7d=5,
            recency_intensity=0.7,
            overall_trend_score=0.7,
            historical_status="new",
        )
        
        calculator = TrendMetricsCalculator()
        metrics = calculator.calculate(features)
        
        assert metrics.is_emerging
        assert metrics.stage in (TrendStageLabel.EMERGING, TrendStageLabel.RISING)

    def test_detect_signals(self):
        """Test signal detection."""
        features = TrendFeatures(
            topic_id=1,
            growth_rate_7d=0.5,
            source_diversity_score=0.6,
            has_recent_release=True,
        )
        
        calculator = TrendMetricsCalculator()
        signals = calculator._detect_signals(features)
        
        signal_types = [s.signal_type for s in signals]
        assert TrendSignalType.GROWTH in signal_types
        assert TrendSignalType.DIVERSITY in signal_types
        assert TrendSignalType.RELEASE in signal_types


class TestTrendSignalResult:
    """Tests for TrendSignalResult."""

    def test_create_signal_result(self):
        """Test creating a signal result."""
        signal = TrendSignalResult(
            signal_type="growth",
            strength=0.8,
            description="High growth rate",
            evidence=["10 items in 7 days"],
        )
        assert signal.signal_type == "growth"
        assert signal.strength == 0.8

    def test_signal_to_dict(self):
        """Test converting signal to dict."""
        signal = TrendSignalResult(
            signal_type="growth",
            strength=0.8,
            description="High growth",
            evidence=["evidence1"],
        )
        data = signal.to_dict()
        assert data["signal_type"] == "growth"
        assert data["strength"] == 0.8


class TestTrendMetrics:
    """Tests for TrendMetrics."""

    def test_create_trend_metrics(self):
        """Test creating trend metrics."""
        metrics = TrendMetrics(
            topic_id=1,
            trend_score=0.7,
            stage=TrendStageLabel.RISING,
            signals=[],
            is_emerging=True,
            recommended_for_homepage=False,
            confidence=0.8,
            computed_at=datetime.now(timezone.utc),
        )
        assert metrics.topic_id == 1
        assert metrics.trend_score == 0.7
        assert metrics.is_emerging

    def test_metrics_to_dict(self):
        """Test converting metrics to dict."""
        metrics = TrendMetrics(
            topic_id=1,
            trend_score=0.7,
            stage=TrendStageLabel.RISING,
            signals=[],
            is_emerging=True,
            recommended_for_homepage=False,
            confidence=0.8,
            computed_at=datetime.now(timezone.utc),
        )
        data = metrics.to_dict()
        assert data["topic_id"] == 1
        assert data["stage"] == "rising"
        assert data["is_emerging"] is True


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_extract_trend_features(self):
        """Test extract_trend_features function."""
        features = extract_trend_features(
            topic_id=1,
            topic_data={"item_count": 5},
        )
        assert features.topic_id == 1
        assert features.item_count_total == 5

    def test_calculate_trend_metrics(self):
        """Test calculate_trend_metrics function."""
        metrics = calculate_trend_metrics(
            topic_id=1,
            topic_data={"item_count": 5},
        )
        assert metrics.topic_id == 1
        assert isinstance(metrics.stage, TrendStageLabel)
