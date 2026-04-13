"""Retrieval policies for different use cases.

Defines different retrieval modes and their configurations
for various agent scenarios.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class RetrievalMode(StrEnum):
    """Retrieval mode types."""

    TOPIC_CONTEXT = "topic_context"  # For general topic context
    ENTITY_CONTEXT = "entity_context"  # For entity-focused retrieval
    HISTORIAN = "historian"  # For Historian agent
    ANALYST = "analyst"  # For Analyst agent
    QUICK = "quick"  # Fast retrieval with minimal data
    FULL = "full"  # Complete retrieval with all data


@dataclass
class RetrievalPolicy:
    """Configuration for a retrieval policy."""

    mode: RetrievalMode

    # What to include
    include_topic_memory: bool = True
    include_snapshots: bool = True
    include_timeline: bool = True
    include_judgements: bool = True
    include_entity_memories: bool = False
    include_related_topics: bool = False
    include_semantic_search: bool = False

    # Limits
    max_snapshots: int = 10
    max_timeline_events: int = 50
    max_judgements: int = 20
    max_entity_memories: int = 10
    max_related_topics: int = 10
    max_semantic_results: int = 5

    # Filters
    judgement_types: list[str] = field(default_factory=list)
    timeline_event_types: list[str] = field(default_factory=list)
    min_importance_score: float = 0.0

    # Semantic search
    semantic_query: str | None = None


# Predefined policies
TOPIC_CONTEXT_POLICY = RetrievalPolicy(
    mode=RetrievalMode.TOPIC_CONTEXT,
    include_topic_memory=True,
    include_snapshots=True,
    include_timeline=True,
    include_judgements=True,
    include_entity_memories=False,
    include_related_topics=False,
    max_snapshots=5,
    max_timeline_events=30,
    max_judgements=10,
)

ENTITY_CONTEXT_POLICY = RetrievalPolicy(
    mode=RetrievalMode.ENTITY_CONTEXT,
    include_topic_memory=False,
    include_snapshots=False,
    include_timeline=False,
    include_judgements=True,
    include_entity_memories=True,
    include_related_topics=True,
    max_entity_memories=20,
    max_related_topics=20,
    max_judgements=10,
)

HISTORIAN_POLICY = RetrievalPolicy(
    mode=RetrievalMode.HISTORIAN,
    include_topic_memory=True,
    include_snapshots=True,
    include_timeline=True,
    include_judgements=True,
    include_entity_memories=True,
    include_related_topics=True,
    include_semantic_search=True,
    max_snapshots=20,
    max_timeline_events=100,
    max_judgements=30,
    max_entity_memories=10,
    max_related_topics=10,
    max_semantic_results=10,
)

ANALYST_POLICY = RetrievalPolicy(
    mode=RetrievalMode.ANALYST,
    include_topic_memory=True,
    include_snapshots=True,
    include_timeline=True,
    include_judgements=True,
    include_entity_memories=False,
    include_related_topics=True,
    include_semantic_search=False,
    max_snapshots=10,
    max_timeline_events=50,
    max_judgements=20,
    max_related_topics=5,
    judgement_types=["importance", "trend", "classification"],
)

QUICK_POLICY = RetrievalPolicy(
    mode=RetrievalMode.QUICK,
    include_topic_memory=True,
    include_snapshots=True,
    include_timeline=False,
    include_judgements=False,
    include_entity_memories=False,
    include_related_topics=False,
    max_snapshots=1,
)

FULL_POLICY = RetrievalPolicy(
    mode=RetrievalMode.FULL,
    include_topic_memory=True,
    include_snapshots=True,
    include_timeline=True,
    include_judgements=True,
    include_entity_memories=True,
    include_related_topics=True,
    include_semantic_search=True,
    max_snapshots=50,
    max_timeline_events=200,
    max_judgements=50,
    max_entity_memories=20,
    max_related_topics=20,
    max_semantic_results=20,
)


def get_policy(mode: RetrievalMode | str) -> RetrievalPolicy:
    """Get a predefined retrieval policy.

    Args:
        mode: Retrieval mode.

    Returns:
        RetrievalPolicy for the mode.
    """
    if isinstance(mode, str):
        mode = RetrievalMode(mode)

    policies = {
        RetrievalMode.TOPIC_CONTEXT: TOPIC_CONTEXT_POLICY,
        RetrievalMode.ENTITY_CONTEXT: ENTITY_CONTEXT_POLICY,
        RetrievalMode.HISTORIAN: HISTORIAN_POLICY,
        RetrievalMode.ANALYST: ANALYST_POLICY,
        RetrievalMode.QUICK: QUICK_POLICY,
        RetrievalMode.FULL: FULL_POLICY,
    }

    return policies.get(mode, TOPIC_CONTEXT_POLICY)
