"""Report DTO definitions."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TrendSignalDTO(BaseModel):
    """DTO for trend signal."""

    id: int | None = None
    topic_id: int
    signal_type: str
    signal_strength: float = 0.5
    window_start: datetime
    window_end: datetime
    evidence_count: int = 0
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    stage_label: str | None = None
    status: str = "active"
    detected_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrendCardDTO(BaseModel):
    """DTO for trend card display."""

    topic_id: int
    trend_title: str
    trend_summary: str
    signal_summary: str
    stage_label: str
    momentum_indicator: str | None = None
    watch_points: list[str] = Field(default_factory=list)
    signals: list[TrendSignalDTO] = Field(default_factory=list)
    heat_score: float = 0.0
    trend_score: float = 0.0


class ReportTopicSummaryDTO(BaseModel):
    """Summary of a topic for reports."""

    topic_id: int
    title: str
    summary: str
    why_it_matters: str | None = None
    trend_stage: str | None = None
    heat_score: float = 0.0


class ReportSectionDTO(BaseModel):
    """DTO for a report section."""

    section_id: str
    section_title: str
    section_intro: str
    key_points: list[str] = Field(default_factory=list)
    topic_summaries: list[ReportTopicSummaryDTO] = Field(default_factory=list)
    closing_note: str | None = None
    editorial_note: str | None = None


class ReportDTO(BaseModel):
    """DTO for a complete report."""

    id: int | None = None
    report_type: str  # daily, weekly
    report_date: datetime
    title: str
    executive_summary: str
    sections: list[ReportSectionDTO] = Field(default_factory=list)
    topic_count: int = 0
    generated_at: datetime | None = None
    status: str = "draft"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReportCreateDTO(BaseModel):
    """DTO for creating a report."""

    report_type: str
    report_date: datetime
    title: str
    executive_summary: str
    sections: list[ReportSectionDTO] = Field(default_factory=list)
    topic_ids: list[int] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
