"""Memory related DTOs for complex memory system."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ============ Working Memory ============

class WorkingMemoryDTO(BaseModel):
    """Working memory for current agent session."""

    session_id: str
    agent_name: str
    current_context: dict[str, Any] = Field(default_factory=dict)
    recent_observations: list[str] = Field(default_factory=list)
    pending_actions: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SessionMemoryDTO(BaseModel):
    """Session-level memory across agent runs."""

    session_id: str
    user_id: str | None = None
    started_at: datetime
    last_active_at: datetime
    context: dict[str, Any] = Field(default_factory=dict)
    history: list[dict[str, Any]] = Field(default_factory=list)


# ============ Topic Memory ============

class TopicMemoryDTO(BaseModel):
    """Long-term memory for a topic."""

    id: int | None = None
    topic_id: int
    first_seen_at: datetime
    last_seen_at: datetime
    historical_status: str = "new"  # new, evolving, recurring, milestone
    current_stage: str = "emerging"  # emerging, active, stable, declining
    history_summary: str | None = None
    key_milestones: list[dict[str, Any]] = Field(default_factory=list)
    last_refreshed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TopicSnapshotDTO(BaseModel):
    """Point-in-time snapshot of a topic."""

    id: int | None = None
    topic_id: int
    snapshot_at: datetime
    summary: str | None = None
    why_it_matters: str | None = None
    system_judgement: str | None = None
    heat_score: float = 0.0
    trend_score: float = 0.0
    item_count: int = 0
    source_count: int = 0
    representative_item_id: int | None = None
    timeline_json: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TopicMemoryCreateDTO(BaseModel):
    """DTO for creating topic memory."""

    topic_id: int
    first_seen_at: datetime
    historical_status: str = "new"
    current_stage: str = "emerging"
    history_summary: str | None = None


class TopicSnapshotCreateDTO(BaseModel):
    """DTO for creating topic snapshot."""

    topic_id: int
    summary: str | None = None
    why_it_matters: str | None = None
    system_judgement: str | None = None
    heat_score: float = 0.0
    trend_score: float = 0.0
    item_count: int = 0
    source_count: int = 0
    representative_item_id: int | None = None


# ============ Entity Memory ============

class EntityMemoryDTO(BaseModel):
    """Long-term memory for an entity."""

    id: int | None = None
    entity_id: int
    summary: str | None = None
    related_topic_ids: list[int] = Field(default_factory=list)
    milestones: list[dict[str, Any]] = Field(default_factory=list)
    recent_signals: list[dict[str, Any]] = Field(default_factory=list)
    last_refreshed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EntityMemoryCreateDTO(BaseModel):
    """DTO for creating entity memory."""

    entity_id: int
    summary: str | None = None


# ============ Judgement Memory ============

class JudgementMemoryDTO(BaseModel):
    """Record of a system judgement."""

    id: int | None = None
    target_type: str  # topic, entity, item
    target_id: int
    agent_name: str
    judgement_type: str  # importance, trend, classification, etc.
    judgement: str
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    later_outcome: str | None = None  # For validation
    metadata: dict[str, Any] = Field(default_factory=dict)


class JudgementCreateDTO(BaseModel):
    """DTO for creating judgement record."""

    target_type: str
    target_id: int
    agent_name: str
    judgement_type: str
    judgement: str
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)


# ============ Timeline ============

class TimelinePointDTO(BaseModel):
    """A point on a timeline."""

    event_time: datetime
    event_type: str
    title: str
    description: str | None = None
    source_item_id: int | None = None
    source_type: str | None = None
    importance_score: float = 0.5
    metadata: dict[str, Any] = Field(default_factory=dict)


class TimelineEventDTO(BaseModel):
    """Full timeline event with ID."""

    id: int | None = None
    topic_id: int
    event_time: datetime
    event_type: str
    title: str
    description: str | None = None
    source_item_id: int | None = None
    source_type: str | None = None
    importance_score: float = 0.5
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


# ============ Retrieval ============

class MemoryRetrievalResultDTO(BaseModel):
    """Result of memory retrieval operation."""

    topic_memory: TopicMemoryDTO | None = None
    snapshots: list[TopicSnapshotDTO] = Field(default_factory=list)
    timeline: list[TimelinePointDTO] = Field(default_factory=list)
    entity_memories: list[EntityMemoryDTO] = Field(default_factory=list)
    related_topics: list[int] = Field(default_factory=list)
    judgements: list[JudgementMemoryDTO] = Field(default_factory=list)
    retrieval_time_ms: float = 0.0


class TopicHistoryContextDTO(BaseModel):
    """Complete historical context for a topic."""

    topic_id: int
    topic_memory: TopicMemoryDTO | None = None
    latest_snapshot: TopicSnapshotDTO | None = None
    timeline: list[TimelinePointDTO] = Field(default_factory=list)
    related_entity_ids: list[int] = Field(default_factory=list)
    recent_judgements: list[JudgementMemoryDTO] = Field(default_factory=list)
    similar_past_topics: list[int] = Field(default_factory=list)
