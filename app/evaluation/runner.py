"""Evaluation runner for automated quality assessment."""

import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from app.bootstrap.logging import get_logger
from app.evaluation.dataset import DatasetLoader
from app.evaluation.metrics import (
    MetricResult,
    board_classification_accuracy,
    historian_consistency,
    topic_merge_f1,
    topic_merge_precision,
    topic_merge_recall,
)
from app.evaluation.schemas import (
    DatasetDTO,
    EvaluationConfigDTO,
    EvaluationRunDTO,
    EvaluationStatus,
    EvaluationSummaryDTO,
    EvaluationThresholdsDTO,
    EvaluationType,
    MetricResultDTO,
)

logger = get_logger(__name__)


class EvaluationRunner:
    """Runner for evaluation tasks."""

    def __init__(
        self,
        dataset_loader: DatasetLoader | None = None,
        thresholds: EvaluationThresholdsDTO | None = None,
    ) -> None:
        """Initialize the runner.

        Args:
            dataset_loader: Dataset loader.
            thresholds: Evaluation thresholds.
        """
        self._dataset_loader = dataset_loader or DatasetLoader()
        self._thresholds = thresholds or EvaluationThresholdsDTO()
        self._evaluators: dict[EvaluationType, Callable] = {
            EvaluationType.BOARD_CLASSIFICATION: self._run_board_classification_eval,
            EvaluationType.TOPIC_MERGE: self._run_topic_merge_eval,
            EvaluationType.HISTORIAN_QUALITY: self._run_historian_eval,
        }

    def run(
        self,
        config: EvaluationConfigDTO,
    ) -> EvaluationRunDTO:
        """Run an evaluation.

        Args:
            config: Evaluation configuration.

        Returns:
            Evaluation run result.
        """
        run_id = str(uuid.uuid4())[:8]
        started_at = datetime.now(timezone.utc)

        logger.info(f"Starting evaluation run {run_id}: {config.evaluation_type}")

        run = EvaluationRunDTO(
            id=run_id,
            evaluation_type=config.evaluation_type,
            status=EvaluationStatus.RUNNING,
            started_at=started_at,
            config=config.model_dump(),
        )

        try:
            # Load dataset
            dataset = self._dataset_loader.load_dataset(
                config.evaluation_type,
                version="1.0",
            )

            if not dataset.samples:
                run.status = EvaluationStatus.FAILED
                run.errors.append("No samples in dataset")
                return run

            # Apply sample limit
            samples = dataset.samples
            if config.sample_limit:
                samples = samples[:config.sample_limit]

            # Run evaluator
            evaluator = self._evaluators.get(config.evaluation_type)
            if not evaluator:
                run.status = EvaluationStatus.FAILED
                run.errors.append(f"No evaluator for {config.evaluation_type}")
                return run

            metrics = evaluator(samples, config)

            # Convert to DTOs
            run.metrics = [
                MetricResultDTO(
                    name=m.name,
                    category=m.category.value,
                    value=m.value,
                    details=m.details,
                    sample_size=m.sample_size,
                    confidence=m.confidence,
                )
                for m in metrics
            ]

            # Generate summary
            run.summary = self._generate_summary(metrics, config.evaluation_type)
            run.status = EvaluationStatus.COMPLETED

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            run.status = EvaluationStatus.FAILED
            run.errors.append(str(e))

        run.completed_at = datetime.now(timezone.utc)
        run.duration_seconds = (run.completed_at - started_at).total_seconds()

        logger.info(
            f"Evaluation run {run_id} completed: {run.status}, "
            f"duration={run.duration_seconds:.2f}s"
        )

        return run

    def run_all(
        self,
        sample_limit: int | None = None,
    ) -> list[EvaluationRunDTO]:
        """Run all available evaluations.

        Args:
            sample_limit: Optional sample limit per evaluation.

        Returns:
            List of evaluation runs.
        """
        runs = []
        for eval_type in self._evaluators.keys():
            config = EvaluationConfigDTO(
                evaluation_type=eval_type,
                sample_limit=sample_limit,
            )
            run = self.run(config)
            runs.append(run)
        return runs

    def _run_board_classification_eval(
        self,
        samples: list,
        config: EvaluationConfigDTO,
    ) -> list[MetricResult]:
        """Run board classification evaluation.

        Args:
            samples: Dataset samples.
            config: Evaluation config.

        Returns:
            List of metric results.
        """
        # Extract predictions and labels
        # In real implementation, would call classifier
        predictions = []
        labels = []

        for sample in samples:
            # Simulate prediction (in real impl, call classifier)
            input_data = sample.input_data
            expected = sample.expected_output

            # Simple heuristic for demo
            title = input_data.get("title", "").lower()
            if any(kw in title for kw in ["release", "framework", "kubernetes", "react", "python", "rust", "copilot"]):
                pred = "tech"
            else:
                pred = "news"

            predictions.append(pred)
            labels.append(expected.get("board_type", "unknown"))

        # Calculate metrics
        accuracy = board_classification_accuracy(predictions, labels)

        return [accuracy]

    def _run_topic_merge_eval(
        self,
        samples: list,
        config: EvaluationConfigDTO,
    ) -> list[MetricResult]:
        """Run topic merge evaluation.

        Args:
            samples: Dataset samples.
            config: Evaluation config.

        Returns:
            List of metric results.
        """
        predicted_merges = []
        actual_merges = []

        for sample in samples:
            input_data = sample.input_data
            expected = sample.expected_output

            topic_a = input_data.get("topic_a", {})
            topic_b = input_data.get("topic_b", {})
            should_merge = expected.get("should_merge", False)

            # Simulate merge prediction (in real impl, call merge service)
            # Simple heuristic: check title similarity
            title_a = topic_a.get("title", "").lower()
            title_b = topic_b.get("title", "").lower()

            words_a = set(title_a.split())
            words_b = set(title_b.split())
            overlap = len(words_a & words_b) / max(len(words_a | words_b), 1)

            pred_merge = overlap > 0.3

            if pred_merge:
                predicted_merges.append((topic_a.get("id", 0), topic_b.get("id", 0)))

            if should_merge:
                actual_merges.append((topic_a.get("id", 0), topic_b.get("id", 0)))

        # Calculate metrics
        precision = topic_merge_precision(predicted_merges, actual_merges)
        recall = topic_merge_recall(predicted_merges, actual_merges)
        f1 = topic_merge_f1(predicted_merges, actual_merges)

        return [precision, recall, f1]

    def _run_historian_eval(
        self,
        samples: list,
        config: EvaluationConfigDTO,
    ) -> list[MetricResult]:
        """Run historian quality evaluation.

        Args:
            samples: Dataset samples.
            config: Evaluation config.

        Returns:
            List of metric results.
        """
        # Simulate historian outputs
        outputs = []
        for sample in samples:
            # In real impl, would call historian agent
            output = {
                "historical_context": "This topic relates to previous developments...",
                "timeline_events": [{"date": "2024-01-01", "event": "Initial release"}],
                "related_topics": [1, 2, 3],
            }
            outputs.append(output)

        consistency = historian_consistency(outputs)

        return [consistency]

    def _generate_summary(
        self,
        metrics: list[MetricResult],
        eval_type: EvaluationType,
    ) -> dict[str, Any]:
        """Generate evaluation summary.

        Args:
            metrics: Metric results.
            eval_type: Evaluation type.

        Returns:
            Summary dict.
        """
        summary: dict[str, Any] = {
            "metrics": {m.name: m.value for m in metrics},
            "passed": True,
            "failed_metrics": [],
        }

        # Check against thresholds
        threshold_map = {
            "board_classification_accuracy": self._thresholds.board_classification_accuracy,
            "topic_merge_precision": self._thresholds.topic_merge_precision,
            "topic_merge_recall": self._thresholds.topic_merge_recall,
            "historian_consistency": self._thresholds.historian_consistency,
        }

        for metric in metrics:
            threshold = threshold_map.get(metric.name)
            if threshold and metric.value < threshold:
                summary["passed"] = False
                summary["failed_metrics"].append({
                    "name": metric.name,
                    "value": metric.value,
                    "threshold": threshold,
                })

        return summary

    def get_summary(
        self,
        run: EvaluationRunDTO,
    ) -> EvaluationSummaryDTO:
        """Get evaluation summary.

        Args:
            run: Evaluation run.

        Returns:
            Evaluation summary.
        """
        metrics_dict = {m.name: m.value for m in run.metrics}
        overall_score = sum(metrics_dict.values()) / len(metrics_dict) if metrics_dict else 0.0

        return EvaluationSummaryDTO(
            evaluation_type=run.evaluation_type,
            run_id=run.id,
            timestamp=run.started_at,
            overall_score=overall_score,
            metrics=metrics_dict,
            passed=run.summary.get("passed", False),
            thresholds={},
            recommendations=self._generate_recommendations(run),
        )

    def _generate_recommendations(
        self,
        run: EvaluationRunDTO,
    ) -> list[str]:
        """Generate recommendations based on results.

        Args:
            run: Evaluation run.

        Returns:
            List of recommendations.
        """
        recommendations = []

        for metric in run.metrics:
            if metric.value < 0.5:
                recommendations.append(
                    f"Critical: {metric.name} is below 50%. Review implementation."
                )
            elif metric.value < 0.7:
                recommendations.append(
                    f"Warning: {metric.name} is below 70%. Consider improvements."
                )

        if not recommendations:
            recommendations.append("All metrics are within acceptable ranges.")

        return recommendations


# Convenience functions

def run_board_classification_eval(
    sample_limit: int | None = None,
) -> EvaluationRunDTO:
    """Run board classification evaluation.

    Args:
        sample_limit: Optional sample limit.

    Returns:
        Evaluation run.
    """
    runner = EvaluationRunner()
    config = EvaluationConfigDTO(
        evaluation_type=EvaluationType.BOARD_CLASSIFICATION,
        sample_limit=sample_limit,
    )
    return runner.run(config)


def run_topic_merge_eval(
    sample_limit: int | None = None,
) -> EvaluationRunDTO:
    """Run topic merge evaluation.

    Args:
        sample_limit: Optional sample limit.

    Returns:
        Evaluation run.
    """
    runner = EvaluationRunner()
    config = EvaluationConfigDTO(
        evaluation_type=EvaluationType.TOPIC_MERGE,
        sample_limit=sample_limit,
    )
    return runner.run(config)


def run_historian_eval(
    sample_limit: int | None = None,
) -> EvaluationRunDTO:
    """Run historian evaluation.

    Args:
        sample_limit: Optional sample limit.

    Returns:
        Evaluation run.
    """
    runner = EvaluationRunner()
    config = EvaluationConfigDTO(
        evaluation_type=EvaluationType.HISTORIAN_QUALITY,
        sample_limit=sample_limit,
    )
    return runner.run(config)


def run_writer_review_eval(
    sample_limit: int | None = None,
) -> EvaluationRunDTO:
    """Run writer/review evaluation.

    Args:
        sample_limit: Optional sample limit.

    Returns:
        Evaluation run.
    """
    runner = EvaluationRunner()
    config = EvaluationConfigDTO(
        evaluation_type=EvaluationType.WRITER_QUALITY,
        sample_limit=sample_limit,
    )
    return runner.run(config)
