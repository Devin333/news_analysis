"""Cost optimization policies for intelligent resource usage."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any

from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


class ModelTier(StrEnum):
    """Model tier for cost optimization."""

    SMALL = "small"  # Fast, cheap (gpt-4o-mini, claude-3-haiku)
    MEDIUM = "medium"  # Balanced (gpt-4o, claude-3-sonnet)
    LARGE = "large"  # High quality (gpt-4, claude-3-opus)


class TaskComplexity(StrEnum):
    """Task complexity levels."""

    SIMPLE = "simple"  # Classification, extraction
    MODERATE = "moderate"  # Summarization, analysis
    COMPLEX = "complex"  # Reasoning, generation


@dataclass
class CostPolicyConfig:
    """Configuration for cost policies."""

    # Model selection
    default_tier: ModelTier = ModelTier.MEDIUM
    use_small_for_simple: bool = True
    use_large_for_reports: bool = True

    # Skip conditions
    skip_low_value_topics: bool = True
    low_value_threshold: float = 0.3
    skip_if_recently_processed: bool = True
    recent_hours: int = 24

    # Caching
    cache_writer_output: bool = True
    cache_ttl_hours: int = 48

    # Batch optimization
    batch_embeddings: bool = True
    max_batch_size: int = 100


# Default model mapping
MODEL_TIER_MAP = {
    ModelTier.SMALL: {
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-haiku",
    },
    ModelTier.MEDIUM: {
        "openai": "gpt-4o",
        "anthropic": "claude-3-sonnet",
    },
    ModelTier.LARGE: {
        "openai": "gpt-4",
        "anthropic": "claude-3-opus",
    },
}


class CostOptimizationPolicies:
    """Policies for cost optimization."""

    def __init__(self, config: CostPolicyConfig | None = None) -> None:
        """Initialize policies.

        Args:
            config: Policy configuration.
        """
        self._config = config or CostPolicyConfig()

    def should_skip_topic(
        self,
        topic_value_score: float,
        last_processed_at: datetime | None = None,
    ) -> tuple[bool, str]:
        """Determine if topic processing should be skipped.

        Args:
            topic_value_score: Topic value/importance score.
            last_processed_at: When topic was last processed.

        Returns:
            Tuple of (should_skip, reason).
        """
        # Check low value
        if self._config.skip_low_value_topics:
            if topic_value_score < self._config.low_value_threshold:
                return True, f"Low value topic (score={topic_value_score:.2f})"

        # Check recently processed
        if self._config.skip_if_recently_processed and last_processed_at:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=self._config.recent_hours)
            if last_processed_at > cutoff:
                return True, f"Recently processed ({last_processed_at})"

        return False, ""

    def select_model_tier(
        self,
        task_type: str,
        task_complexity: TaskComplexity = TaskComplexity.MODERATE,
        is_report: bool = False,
        is_uncertain: bool = False,
    ) -> ModelTier:
        """Select appropriate model tier for task.

        Args:
            task_type: Type of task.
            task_complexity: Task complexity.
            is_report: Whether this is for a report.
            is_uncertain: Whether result is uncertain.

        Returns:
            Recommended model tier.
        """
        # Reports always use large model
        if is_report and self._config.use_large_for_reports:
            return ModelTier.LARGE

        # Uncertain cases use large model
        if is_uncertain:
            return ModelTier.LARGE

        # Simple tasks use small model
        if task_complexity == TaskComplexity.SIMPLE and self._config.use_small_for_simple:
            return ModelTier.SMALL

        # Complex tasks use large model
        if task_complexity == TaskComplexity.COMPLEX:
            return ModelTier.LARGE

        return self._config.default_tier

    def get_model_name(
        self,
        tier: ModelTier,
        provider: str = "openai",
    ) -> str:
        """Get model name for tier and provider.

        Args:
            tier: Model tier.
            provider: Model provider.

        Returns:
            Model name.
        """
        return MODEL_TIER_MAP.get(tier, {}).get(provider, "gpt-4o-mini")

    def should_cache_result(
        self,
        task_type: str,
        has_changes: bool = True,
    ) -> bool:
        """Determine if result should be cached.

        Args:
            task_type: Type of task.
            has_changes: Whether there are changes from previous.

        Returns:
            Whether to cache.
        """
        if task_type == "writer" and self._config.cache_writer_output:
            return not has_changes  # Cache if no changes

        return False

    def should_skip_historian(
        self,
        last_run_at: datetime | None,
        topic_changed: bool = False,
    ) -> tuple[bool, str]:
        """Determine if historian should be skipped.

        Args:
            last_run_at: When historian last ran.
            topic_changed: Whether topic has changed.

        Returns:
            Tuple of (should_skip, reason).
        """
        if topic_changed:
            return False, ""

        if last_run_at:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=self._config.recent_hours)
            if last_run_at > cutoff:
                return True, "Historian recently ran and topic unchanged"

        return False, ""

    def get_batch_config(self) -> dict[str, Any]:
        """Get batch processing configuration.

        Returns:
            Batch config dict.
        """
        return {
            "enabled": self._config.batch_embeddings,
            "max_size": self._config.max_batch_size,
        }


class ModelSelectionPolicy:
    """Policy for selecting models based on task."""

    # Task to complexity mapping
    TASK_COMPLEXITY = {
        "classify_board": TaskComplexity.SIMPLE,
        "classify_content_type": TaskComplexity.SIMPLE,
        "extract_entities": TaskComplexity.SIMPLE,
        "generate_tags": TaskComplexity.SIMPLE,
        "summarize": TaskComplexity.MODERATE,
        "analyze_importance": TaskComplexity.MODERATE,
        "generate_timeline": TaskComplexity.MODERATE,
        "write_copy": TaskComplexity.COMPLEX,
        "review_copy": TaskComplexity.MODERATE,
        "generate_report": TaskComplexity.COMPLEX,
        "detect_trends": TaskComplexity.MODERATE,
    }

    def __init__(self, policies: CostOptimizationPolicies | None = None) -> None:
        """Initialize policy.

        Args:
            policies: Cost optimization policies.
        """
        self._policies = policies or CostOptimizationPolicies()

    def select_model(
        self,
        task_type: str,
        *,
        provider: str = "openai",
        is_report: bool = False,
        is_uncertain: bool = False,
        override_tier: ModelTier | None = None,
    ) -> str:
        """Select model for task.

        Args:
            task_type: Type of task.
            provider: Model provider.
            is_report: Whether for report.
            is_uncertain: Whether uncertain.
            override_tier: Optional tier override.

        Returns:
            Model name.
        """
        if override_tier:
            return self._policies.get_model_name(override_tier, provider)

        complexity = self.TASK_COMPLEXITY.get(task_type, TaskComplexity.MODERATE)
        tier = self._policies.select_model_tier(
            task_type,
            complexity,
            is_report=is_report,
            is_uncertain=is_uncertain,
        )

        model = self._policies.get_model_name(tier, provider)
        logger.debug(f"Selected model {model} for task {task_type} (tier={tier})")

        return model


class CostAwarePipelinePolicy:
    """Policy for cost-aware pipeline execution."""

    def __init__(
        self,
        policies: CostOptimizationPolicies | None = None,
        model_policy: ModelSelectionPolicy | None = None,
    ) -> None:
        """Initialize policy.

        Args:
            policies: Cost optimization policies.
            model_policy: Model selection policy.
        """
        self._policies = policies or CostOptimizationPolicies()
        self._model_policy = model_policy or ModelSelectionPolicy(self._policies)

    def get_pipeline_config(
        self,
        topic_value_score: float,
        topic_changed: bool,
        last_historian_at: datetime | None = None,
        last_writer_at: datetime | None = None,
        is_for_report: bool = False,
    ) -> dict[str, Any]:
        """Get pipeline configuration based on topic state.

        Args:
            topic_value_score: Topic value score.
            topic_changed: Whether topic changed.
            last_historian_at: Last historian run.
            last_writer_at: Last writer run.
            is_for_report: Whether for report.

        Returns:
            Pipeline configuration.
        """
        config: dict[str, Any] = {
            "run_historian": True,
            "run_analyst": True,
            "run_writer": True,
            "run_reviewer": True,
            "model_tier": ModelTier.MEDIUM,
            "skip_reason": None,
        }

        # Check if should skip entirely
        should_skip, reason = self._policies.should_skip_topic(
            topic_value_score,
            last_writer_at,
        )
        if should_skip and not is_for_report:
            config["run_historian"] = False
            config["run_analyst"] = False
            config["run_writer"] = False
            config["run_reviewer"] = False
            config["skip_reason"] = reason
            return config

        # Check historian skip
        skip_historian, hist_reason = self._policies.should_skip_historian(
            last_historian_at,
            topic_changed,
        )
        if skip_historian:
            config["run_historian"] = False
            logger.debug(f"Skipping historian: {hist_reason}")

        # Select model tier
        if is_for_report:
            config["model_tier"] = ModelTier.LARGE
        elif topic_value_score > 0.8:
            config["model_tier"] = ModelTier.LARGE
        elif topic_value_score < 0.5:
            config["model_tier"] = ModelTier.SMALL

        return config

    def get_model_for_step(
        self,
        step: str,
        config: dict[str, Any],
        provider: str = "openai",
    ) -> str:
        """Get model for pipeline step.

        Args:
            step: Pipeline step name.
            config: Pipeline config.
            provider: Model provider.

        Returns:
            Model name.
        """
        tier = config.get("model_tier", ModelTier.MEDIUM)
        is_report = config.get("is_for_report", False)

        return self._model_policy.select_model(
            step,
            provider=provider,
            is_report=is_report,
            override_tier=tier,
        )
