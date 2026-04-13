"""Evaluation metrics for system quality assessment."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MetricCategory(StrEnum):
    """Metric categories."""

    CLASSIFICATION = "classification"
    CLUSTERING = "clustering"
    AGENT = "agent"
    CONTENT = "content"
    TREND = "trend"
    SYSTEM = "system"


@dataclass
class MetricResult:
    """Result of a metric evaluation."""

    name: str
    category: MetricCategory
    value: float
    details: dict[str, Any] = field(default_factory=dict)
    sample_size: int = 0
    confidence: float | None = None


# ============== Classification Metrics ==============


def board_classification_accuracy(
    predictions: list[str],
    labels: list[str],
) -> MetricResult:
    """Calculate board classification accuracy.

    Args:
        predictions: Predicted board types.
        labels: Ground truth board types.

    Returns:
        MetricResult with accuracy.
    """
    if not predictions or len(predictions) != len(labels):
        return MetricResult(
            name="board_classification_accuracy",
            category=MetricCategory.CLASSIFICATION,
            value=0.0,
            details={"error": "Invalid input"},
        )

    correct = sum(1 for p, l in zip(predictions, labels) if p == l)
    accuracy = correct / len(predictions)

    # Per-class accuracy
    class_correct: dict[str, int] = {}
    class_total: dict[str, int] = {}
    for p, l in zip(predictions, labels):
        class_total[l] = class_total.get(l, 0) + 1
        if p == l:
            class_correct[l] = class_correct.get(l, 0) + 1

    per_class = {
        cls: class_correct.get(cls, 0) / total
        for cls, total in class_total.items()
    }

    return MetricResult(
        name="board_classification_accuracy",
        category=MetricCategory.CLASSIFICATION,
        value=accuracy,
        details={
            "correct": correct,
            "total": len(predictions),
            "per_class_accuracy": per_class,
        },
        sample_size=len(predictions),
    )


def content_type_classification_accuracy(
    predictions: list[str],
    labels: list[str],
) -> MetricResult:
    """Calculate content type classification accuracy.

    Args:
        predictions: Predicted content types.
        labels: Ground truth content types.

    Returns:
        MetricResult with accuracy.
    """
    if not predictions or len(predictions) != len(labels):
        return MetricResult(
            name="content_type_classification_accuracy",
            category=MetricCategory.CLASSIFICATION,
            value=0.0,
        )

    correct = sum(1 for p, l in zip(predictions, labels) if p == l)
    accuracy = correct / len(predictions)

    return MetricResult(
        name="content_type_classification_accuracy",
        category=MetricCategory.CLASSIFICATION,
        value=accuracy,
        sample_size=len(predictions),
    )


# ============== Clustering Metrics ==============


def topic_merge_precision(
    predicted_merges: list[tuple[int, int]],
    actual_merges: list[tuple[int, int]],
) -> MetricResult:
    """Calculate topic merge precision.

    Precision = correct merges / predicted merges

    Args:
        predicted_merges: Predicted merge pairs (topic_a, topic_b).
        actual_merges: Ground truth merge pairs.

    Returns:
        MetricResult with precision.
    """
    if not predicted_merges:
        return MetricResult(
            name="topic_merge_precision",
            category=MetricCategory.CLUSTERING,
            value=0.0,
            details={"error": "No predictions"},
        )

    # Normalize pairs (smaller id first)
    pred_set = {(min(a, b), max(a, b)) for a, b in predicted_merges}
    actual_set = {(min(a, b), max(a, b)) for a, b in actual_merges}

    correct = len(pred_set & actual_set)
    precision = correct / len(pred_set) if pred_set else 0.0

    return MetricResult(
        name="topic_merge_precision",
        category=MetricCategory.CLUSTERING,
        value=precision,
        details={
            "correct_merges": correct,
            "predicted_merges": len(pred_set),
            "actual_merges": len(actual_set),
        },
        sample_size=len(pred_set),
    )


def topic_merge_recall(
    predicted_merges: list[tuple[int, int]],
    actual_merges: list[tuple[int, int]],
) -> MetricResult:
    """Calculate topic merge recall.

    Recall = correct merges / actual merges

    Args:
        predicted_merges: Predicted merge pairs.
        actual_merges: Ground truth merge pairs.

    Returns:
        MetricResult with recall.
    """
    if not actual_merges:
        return MetricResult(
            name="topic_merge_recall",
            category=MetricCategory.CLUSTERING,
            value=0.0,
            details={"error": "No ground truth"},
        )

    pred_set = {(min(a, b), max(a, b)) for a, b in predicted_merges}
    actual_set = {(min(a, b), max(a, b)) for a, b in actual_merges}

    correct = len(pred_set & actual_set)
    recall = correct / len(actual_set) if actual_set else 0.0

    return MetricResult(
        name="topic_merge_recall",
        category=MetricCategory.CLUSTERING,
        value=recall,
        details={
            "correct_merges": correct,
            "actual_merges": len(actual_set),
        },
        sample_size=len(actual_set),
    )


def topic_merge_f1(
    predicted_merges: list[tuple[int, int]],
    actual_merges: list[tuple[int, int]],
) -> MetricResult:
    """Calculate topic merge F1 score.

    Args:
        predicted_merges: Predicted merge pairs.
        actual_merges: Ground truth merge pairs.

    Returns:
        MetricResult with F1.
    """
    precision_result = topic_merge_precision(predicted_merges, actual_merges)
    recall_result = topic_merge_recall(predicted_merges, actual_merges)

    p = precision_result.value
    r = recall_result.value

    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    return MetricResult(
        name="topic_merge_f1",
        category=MetricCategory.CLUSTERING,
        value=f1,
        details={
            "precision": p,
            "recall": r,
        },
    )


# ============== Agent Quality Metrics ==============


def historian_consistency(
    outputs: list[dict[str, Any]],
    expected_patterns: list[str] | None = None,
) -> MetricResult:
    """Evaluate historian agent output consistency.

    Checks:
    - Has historical_context
    - Has timeline_events
    - Has related_topics
    - Consistent structure

    Args:
        outputs: List of historian outputs.
        expected_patterns: Optional expected patterns.

    Returns:
        MetricResult with consistency score.
    """
    if not outputs:
        return MetricResult(
            name="historian_consistency",
            category=MetricCategory.AGENT,
            value=0.0,
        )

    scores = []
    for output in outputs:
        score = 0.0
        checks = 0

        # Check required fields
        if output.get("historical_context"):
            score += 1
        checks += 1

        if output.get("timeline_events"):
            score += 1
        checks += 1

        if output.get("related_topics"):
            score += 1
        checks += 1

        # Check context quality
        context = output.get("historical_context", "")
        if len(context) > 100:
            score += 0.5
        checks += 0.5

        scores.append(score / checks if checks > 0 else 0)

    avg_score = sum(scores) / len(scores)

    return MetricResult(
        name="historian_consistency",
        category=MetricCategory.AGENT,
        value=avg_score,
        details={
            "individual_scores": scores,
            "min_score": min(scores),
            "max_score": max(scores),
        },
        sample_size=len(outputs),
    )


def analyst_value_quality(
    outputs: list[dict[str, Any]],
) -> MetricResult:
    """Evaluate analyst agent output quality.

    Checks:
    - Has importance_score
    - Has key_insights
    - Has impact_assessment
    - Reasonable score ranges

    Args:
        outputs: List of analyst outputs.

    Returns:
        MetricResult with quality score.
    """
    if not outputs:
        return MetricResult(
            name="analyst_value_quality",
            category=MetricCategory.AGENT,
            value=0.0,
        )

    scores = []
    for output in outputs:
        score = 0.0
        checks = 0

        # Check importance score
        importance = output.get("importance_score")
        if importance is not None and 0 <= importance <= 1:
            score += 1
        checks += 1

        # Check key insights
        insights = output.get("key_insights", [])
        if insights and len(insights) >= 1:
            score += 1
        checks += 1

        # Check impact assessment
        if output.get("impact_assessment"):
            score += 1
        checks += 1

        # Check reasoning
        if output.get("reasoning"):
            score += 0.5
        checks += 0.5

        scores.append(score / checks if checks > 0 else 0)

    avg_score = sum(scores) / len(scores)

    return MetricResult(
        name="analyst_value_quality",
        category=MetricCategory.AGENT,
        value=avg_score,
        sample_size=len(outputs),
    )


def writer_faithfulness(
    copies: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> MetricResult:
    """Evaluate writer output faithfulness to sources.

    Checks if generated copy is faithful to source material.

    Args:
        copies: Generated copies.
        sources: Source materials.

    Returns:
        MetricResult with faithfulness score.
    """
    if not copies or len(copies) != len(sources):
        return MetricResult(
            name="writer_faithfulness",
            category=MetricCategory.AGENT,
            value=0.0,
        )

    # Simplified check - in production would use NLI model
    scores = []
    for copy, source in zip(copies, sources):
        score = 0.0

        copy_text = copy.get("summary", "") + " " + copy.get("body", "")
        source_text = source.get("content", "")

        # Check key terms overlap
        copy_terms = set(copy_text.lower().split())
        source_terms = set(source_text.lower().split())

        if source_terms:
            overlap = len(copy_terms & source_terms) / len(source_terms)
            score = min(1.0, overlap * 2)  # Scale up

        scores.append(score)

    avg_score = sum(scores) / len(scores)

    return MetricResult(
        name="writer_faithfulness",
        category=MetricCategory.AGENT,
        value=avg_score,
        sample_size=len(copies),
    )


def reviewer_catch_rate(
    review_decisions: list[str],
    actual_issues: list[bool],
) -> MetricResult:
    """Evaluate reviewer's ability to catch issues.

    Args:
        review_decisions: Reviewer decisions (approved/rejected).
        actual_issues: Whether content actually had issues.

    Returns:
        MetricResult with catch rate.
    """
    if not review_decisions or len(review_decisions) != len(actual_issues):
        return MetricResult(
            name="reviewer_catch_rate",
            category=MetricCategory.AGENT,
            value=0.0,
        )

    # True positives: rejected and had issues
    # False negatives: approved but had issues
    true_positives = 0
    false_negatives = 0
    total_issues = 0

    for decision, has_issue in zip(review_decisions, actual_issues):
        if has_issue:
            total_issues += 1
            if decision == "rejected":
                true_positives += 1
            else:
                false_negatives += 1

    catch_rate = true_positives / total_issues if total_issues > 0 else 1.0

    return MetricResult(
        name="reviewer_catch_rate",
        category=MetricCategory.AGENT,
        value=catch_rate,
        details={
            "true_positives": true_positives,
            "false_negatives": false_negatives,
            "total_issues": total_issues,
        },
        sample_size=len(review_decisions),
    )


# ============== Trend Detection Metrics ==============


def trend_detection_precision(
    predicted_trends: list[int],
    actual_trends: list[int],
) -> MetricResult:
    """Calculate trend detection precision.

    Args:
        predicted_trends: Predicted trending topic IDs.
        actual_trends: Actually trending topic IDs.

    Returns:
        MetricResult with precision.
    """
    if not predicted_trends:
        return MetricResult(
            name="trend_detection_precision",
            category=MetricCategory.TREND,
            value=0.0,
        )

    pred_set = set(predicted_trends)
    actual_set = set(actual_trends)

    correct = len(pred_set & actual_set)
    precision = correct / len(pred_set)

    return MetricResult(
        name="trend_detection_precision",
        category=MetricCategory.TREND,
        value=precision,
        details={
            "correct": correct,
            "predicted": len(pred_set),
            "actual": len(actual_set),
        },
        sample_size=len(pred_set),
    )


def trend_detection_recall(
    predicted_trends: list[int],
    actual_trends: list[int],
) -> MetricResult:
    """Calculate trend detection recall.

    Args:
        predicted_trends: Predicted trending topic IDs.
        actual_trends: Actually trending topic IDs.

    Returns:
        MetricResult with recall.
    """
    if not actual_trends:
        return MetricResult(
            name="trend_detection_recall",
            category=MetricCategory.TREND,
            value=0.0,
        )

    pred_set = set(predicted_trends)
    actual_set = set(actual_trends)

    correct = len(pred_set & actual_set)
    recall = correct / len(actual_set)

    return MetricResult(
        name="trend_detection_recall",
        category=MetricCategory.TREND,
        value=recall,
        sample_size=len(actual_set),
    )


# ============== System Metrics ==============


def pipeline_success_rate(
    total_runs: int,
    successful_runs: int,
) -> MetricResult:
    """Calculate pipeline success rate.

    Args:
        total_runs: Total pipeline runs.
        successful_runs: Successful runs.

    Returns:
        MetricResult with success rate.
    """
    rate = successful_runs / total_runs if total_runs > 0 else 0.0

    return MetricResult(
        name="pipeline_success_rate",
        category=MetricCategory.SYSTEM,
        value=rate,
        details={
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": total_runs - successful_runs,
        },
        sample_size=total_runs,
    )


def average_latency(
    latencies_ms: list[float],
) -> MetricResult:
    """Calculate average latency.

    Args:
        latencies_ms: List of latencies in milliseconds.

    Returns:
        MetricResult with average latency.
    """
    if not latencies_ms:
        return MetricResult(
            name="average_latency",
            category=MetricCategory.SYSTEM,
            value=0.0,
        )

    avg = sum(latencies_ms) / len(latencies_ms)
    p50 = sorted(latencies_ms)[len(latencies_ms) // 2]
    p95_idx = int(len(latencies_ms) * 0.95)
    p95 = sorted(latencies_ms)[min(p95_idx, len(latencies_ms) - 1)]

    return MetricResult(
        name="average_latency",
        category=MetricCategory.SYSTEM,
        value=avg,
        details={
            "p50_ms": p50,
            "p95_ms": p95,
            "min_ms": min(latencies_ms),
            "max_ms": max(latencies_ms),
        },
        sample_size=len(latencies_ms),
    )
