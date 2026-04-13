"""Evaluation schemas and DTOs."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EvaluationType(StrEnum):
    """Evaluation types."""

    BOARD_CLASSIFICATION = "board_classification"
    CONTENT_TYPE_CLASSIFICATION = "content_type_classification"
    TOPIC_MERGE = "topic_merge"
    HISTORIAN_QUALITY = "historian_quality"
    ANALYST_QUALITY = "analyst_quality"
    WRITER_QUALITY = "writer_quality"
    REVIEWER_QUALITY = "reviewer_quality"
    TREND_DETECTION = "trend_detection"
    PIPELINE_HEALTH = "pipeline_health"


class EvaluationStatus(StrEnum):
    """Evaluation run status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class MetricResultDTO(BaseModel):
    """DTO for a metric result."""

    name: str
    category: str
    value: float
    details: dict[str, Any] = Field(default_factory=dict)
    sample_size: int = 0
    confidence: float | None = None


class EvaluationRunDTO(BaseModel):
    """DTO for an evaluation run."""

    id: str
    evaluation_type: EvaluationType
    status: EvaluationStatus
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    metrics: list[MetricResultDTO] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class EvaluationConfigDTO(BaseModel):
    """Configuration for an evaluation run."""

    evaluation_type: EvaluationType
    dataset_path: str | None = None
    sample_limit: int | None = None
    include_details: bool = True
    save_results: bool = True
    custom_params: dict[str, Any] = Field(default_factory=dict)


class EvaluationSummaryDTO(BaseModel):
    """Summary of evaluation results."""

    evaluation_type: EvaluationType
    run_id: str
    timestamp: datetime
    overall_score: float
    metrics: dict[str, float] = Field(default_factory=dict)
    passed: bool
    thresholds: dict[str, float] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)


class DatasetSampleDTO(BaseModel):
    """DTO for a dataset sample."""

    id: str
    input_data: dict[str, Any]
    expected_output: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class DatasetDTO(BaseModel):
    """DTO for an evaluation dataset."""

    name: str
    evaluation_type: EvaluationType
    version: str = "1.0"
    samples: list[DatasetSampleDTO] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class EvaluationThresholdsDTO(BaseModel):
    """Thresholds for evaluation pass/fail."""

    board_classification_accuracy: float = 0.85
    content_type_accuracy: float = 0.80
    topic_merge_precision: float = 0.70
    topic_merge_recall: float = 0.60
    historian_consistency: float = 0.75
    analyst_value_quality: float = 0.70
    writer_faithfulness: float = 0.80
    reviewer_catch_rate: float = 0.85
    trend_detection_precision: float = 0.60
    pipeline_success_rate: float = 0.95


class EvaluationReportDTO(BaseModel):
    """Full evaluation report."""

    report_id: str
    generated_at: datetime
    evaluation_runs: list[EvaluationRunDTO] = Field(default_factory=list)
    overall_health: str  # healthy, degraded, critical
    summary_metrics: dict[str, float] = Field(default_factory=dict)
    trends: dict[str, list[float]] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    comparison_to_baseline: dict[str, float] = Field(default_factory=dict)
