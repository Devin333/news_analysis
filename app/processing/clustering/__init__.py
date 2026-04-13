"""Clustering module for topic aggregation."""

from app.processing.clustering.candidate_retriever import CandidateRetriever
from app.processing.clustering.features import (
    compute_recency_score,
    compute_source_similarity,
    compute_tag_overlap_score,
    compute_title_overlap_score,
)
from app.processing.clustering.merge_scorer import (
    ItemContext,
    MergeScoreResult,
    MergeScorer,
    MergeWeights,
    TopicContext,
)
from app.processing.clustering.policies import (
    MergeDecision,
    MergePolicy,
    PolicyResult,
    get_policy,
)
from app.processing.clustering.similarity import (
    SimilarityCalculator,
    title_similarity,
    summary_similarity,
    tag_similarity,
    time_overlap_score,
)

__all__ = [
    "CandidateRetriever",
    "compute_title_overlap_score",
    "compute_tag_overlap_score",
    "compute_recency_score",
    "compute_source_similarity",
    "ItemContext",
    "MergeDecision",
    "MergePolicy",
    "MergeScoreResult",
    "MergeScorer",
    "MergeWeights",
    "PolicyResult",
    "SimilarityCalculator",
    "TopicContext",
    "get_policy",
    "summary_similarity",
    "tag_similarity",
    "time_overlap_score",
    "title_similarity",
]
