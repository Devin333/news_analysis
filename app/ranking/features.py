"""Ranking feature extraction functions.

Provides individual feature computation functions for topic ranking.
"""

from datetime import datetime, timezone
from typing import Any

from app.contracts.dto.topic import TopicReadDTO


def compute_recency_score(
    last_seen_at: datetime,
    time_window_hours: int = 24,
    now: datetime | None = None,
) -> float:
    """Compute recency score based on last seen time.

    Args:
        last_seen_at: When the topic was last seen
        time_window_hours: Time window for full score
        now: Current time (defaults to UTC now)

    Returns:
        Score between 0.0 and 1.0
    """
    if now is None:
        now = datetime.now(timezone.utc)

    if last_seen_at.tzinfo is None:
        last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)

    age_hours = (now - last_seen_at).total_seconds() / 3600

    if age_hours <= 0:
        return 1.0
    if age_hours >= time_window_hours * 3:
        return 0.0

    # Exponential decay
    decay_rate = 0.693 / time_window_hours  # Half-life = time_window_hours
    return max(0.0, min(1.0, 2.718 ** (-decay_rate * age_hours)))


def compute_stale_penalty(
    last_seen_at: datetime,
    stale_threshold_hours: int = 72,
    now: datetime | None = None,
) -> float:
    """Compute penalty for stale topics.

    Args:
        last_seen_at: When the topic was last seen
        stale_threshold_hours: Hours after which topic is considered stale
        now: Current time

    Returns:
        Penalty between 0.0 (no penalty) and 1.0 (max penalty)
    """
    if now is None:
        now = datetime.now(timezone.utc)

    if last_seen_at.tzinfo is None:
        last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)

    age_hours = (now - last_seen_at).total_seconds() / 3600

    if age_hours < stale_threshold_hours:
        return 0.0

    # Linear increase after threshold
    excess_hours = age_hours - stale_threshold_hours
    return min(1.0, excess_hours / stale_threshold_hours)


def compute_source_diversity_score(
    source_count: int,
    max_sources: int = 10,
) -> float:
    """Compute score based on source diversity.

    Args:
        source_count: Number of unique sources
        max_sources: Maximum sources for full score

    Returns:
        Score between 0.0 and 1.0
    """
    if source_count <= 0:
        return 0.0
    if source_count >= max_sources:
        return 1.0

    # Logarithmic scaling
    import math
    return math.log(source_count + 1) / math.log(max_sources + 1)


def compute_trusted_source_score(
    trusted_source_count: int,
    total_source_count: int,
) -> float:
    """Compute score based on trusted source ratio.

    Args:
        trusted_source_count: Number of trusted sources
        total_source_count: Total number of sources

    Returns:
        Score between 0.0 and 1.0
    """
    if total_source_count <= 0:
        return 0.0

    ratio = trusted_source_count / total_source_count
    # Boost if majority are trusted
    if ratio >= 0.5:
        return 0.5 + ratio * 0.5
    return ratio


def compute_topic_size_score(
    item_count: int,
    min_items: int = 1,
    optimal_items: int = 5,
    max_items: int = 20,
) -> float:
    """Compute score based on topic size.

    Args:
        item_count: Number of items in topic
        min_items: Minimum items for any score
        optimal_items: Optimal number of items
        max_items: Maximum items (beyond this, no extra benefit)

    Returns:
        Score between 0.0 and 1.0
    """
    if item_count < min_items:
        return 0.0
    if item_count >= max_items:
        return 1.0
    if item_count >= optimal_items:
        # Plateau after optimal
        return 0.8 + 0.2 * (item_count - optimal_items) / (max_items - optimal_items)

    # Linear growth to optimal
    return 0.8 * (item_count - min_items) / (optimal_items - min_items)


def compute_trend_signal_score(
    trend_score: float,
    signal_strength: float | None = None,
    stage_label: str | None = None,
) -> float:
    """Compute score based on trend signals.

    Args:
        trend_score: Base trend score from topic
        signal_strength: Optional signal strength from trend_signal
        stage_label: Optional stage label (emerging, growing, peak, etc.)

    Returns:
        Score between 0.0 and 1.0
    """
    base_score = min(1.0, max(0.0, trend_score))

    # Boost based on stage
    stage_boost = {
        "emerging": 0.2,
        "growing": 0.3,
        "peak": 0.1,
        "stable": 0.0,
        "declining": -0.1,
    }

    if stage_label:
        base_score += stage_boost.get(stage_label, 0.0)

    # Factor in signal strength
    if signal_strength is not None:
        base_score = base_score * 0.6 + signal_strength * 0.4

    return min(1.0, max(0.0, base_score))


def compute_analyst_importance_score(
    confidence: float | None,
    trend_momentum: float | None,
    has_why_it_matters: bool,
    has_system_judgement: bool,
) -> float:
    """Compute score based on analyst insight.

    Args:
        confidence: Analyst confidence score
        trend_momentum: Trend momentum from analyst
        has_why_it_matters: Whether why_it_matters is present
        has_system_judgement: Whether system_judgement is present

    Returns:
        Score between 0.0 and 1.0
    """
    score = 0.0

    # Confidence contributes 40%
    if confidence is not None:
        score += confidence * 0.4

    # Trend momentum contributes 30%
    if trend_momentum is not None:
        # Normalize from [-1, 1] to [0, 1]
        normalized_momentum = (trend_momentum + 1) / 2
        score += normalized_momentum * 0.3

    # Content presence contributes 30%
    if has_why_it_matters:
        score += 0.15
    if has_system_judgement:
        score += 0.15

    return min(1.0, max(0.0, score))


def compute_historian_novelty_score(
    is_novel: bool | None,
    historical_context_count: int = 0,
    has_timeline: bool = False,
) -> float:
    """Compute score based on historian analysis.

    Args:
        is_novel: Whether historian marked as novel
        historical_context_count: Number of historical contexts found
        has_timeline: Whether topic has timeline events

    Returns:
        Score between 0.0 and 1.0
    """
    score = 0.5  # Base score

    if is_novel is True:
        score += 0.3
    elif is_novel is False:
        score -= 0.2

    # Historical context adds value
    if historical_context_count > 0:
        score += min(0.2, historical_context_count * 0.05)

    # Timeline presence
    if has_timeline:
        score += 0.1

    return min(1.0, max(0.0, score))


def compute_review_pass_bonus(
    review_status: str | None,
    review_confidence: float | None = None,
) -> float:
    """Compute bonus for passing review.

    Args:
        review_status: Review status (approve, revise, reject)
        review_confidence: Reviewer confidence

    Returns:
        Bonus between 0.0 and 1.0
    """
    if review_status is None:
        return 0.0

    status_scores = {
        "approve": 1.0,
        "revise": 0.3,
        "reject": 0.0,
    }

    base_score = status_scores.get(review_status, 0.0)

    # Factor in confidence
    if review_confidence is not None and review_status == "approve":
        return base_score * (0.7 + review_confidence * 0.3)

    return base_score


def compute_homepage_candidate_score(
    item_count: int,
    source_count: int,
    review_passed: bool,
    recency_score: float,
    trend_score: float,
) -> float:
    """Compute score for homepage candidacy.

    Args:
        item_count: Number of items
        source_count: Number of sources
        review_passed: Whether review passed
        recency_score: Recency score
        trend_score: Trend score

    Returns:
        Score between 0.0 and 1.0
    """
    # Must have multiple sources and items
    if source_count < 2 or item_count < 2:
        return 0.0

    # Must pass review
    if not review_passed:
        return 0.0

    # Weighted combination
    score = (
        recency_score * 0.3
        + trend_score * 0.3
        + compute_source_diversity_score(source_count) * 0.2
        + compute_topic_size_score(item_count) * 0.2
    )

    return min(1.0, max(0.0, score))


def compute_board_weight(
    board_type: str,
    context_board: str | None = None,
) -> float:
    """Compute weight based on board type match.

    Args:
        board_type: Topic's board type
        context_board: Context's target board type

    Returns:
        Weight multiplier (1.0 = neutral)
    """
    if context_board is None:
        return 1.0

    if board_type == context_board:
        return 1.2  # Boost for exact match

    # Cross-board relevance
    relevance_matrix = {
        ("ai", "engineering"): 0.8,
        ("engineering", "ai"): 0.8,
        ("ai", "research"): 0.9,
        ("research", "ai"): 0.9,
        ("engineering", "research"): 0.7,
        ("research", "engineering"): 0.7,
    }

    return relevance_matrix.get((board_type, context_board), 0.5)
