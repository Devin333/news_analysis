"""Cost-aware pipeline for topic processing."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.bootstrap.logging import get_logger
from app.monitoring.cost import CostTracker, get_global_tracker
from app.monitoring.cost_policies import (
    CostAwarePipelinePolicy,
    CostOptimizationPolicies,
    ModelTier,
)

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class CostAwarePipeline:
    """Cost-aware pipeline for topic enrichment.

    Optimizes costs by:
    - Skipping low-value topics
    - Using smaller models for simple tasks
    - Caching results when appropriate
    - Batching operations
    """

    def __init__(
        self,
        policies: CostOptimizationPolicies | None = None,
        cost_tracker: CostTracker | None = None,
    ) -> None:
        """Initialize the pipeline.

        Args:
            policies: Cost optimization policies.
            cost_tracker: Cost tracker.
        """
        self._policies = policies or CostOptimizationPolicies()
        self._pipeline_policy = CostAwarePipelinePolicy(self._policies)
        self._cost_tracker = cost_tracker or get_global_tracker()

    async def process_topic(
        self,
        topic_id: int,
        topic_value_score: float,
        topic_changed: bool = True,
        last_historian_at: datetime | None = None,
        last_writer_at: datetime | None = None,
        is_for_report: bool = False,
    ) -> dict[str, Any]:
        """Process a topic with cost optimization.

        Args:
            topic_id: Topic ID.
            topic_value_score: Topic value/importance score.
            topic_changed: Whether topic has changed.
            last_historian_at: Last historian run time.
            last_writer_at: Last writer run time.
            is_for_report: Whether processing for report.

        Returns:
            Processing result.
        """
        start_time = datetime.now(timezone.utc)

        # Get pipeline configuration
        config = self._pipeline_policy.get_pipeline_config(
            topic_value_score=topic_value_score,
            topic_changed=topic_changed,
            last_historian_at=last_historian_at,
            last_writer_at=last_writer_at,
            is_for_report=is_for_report,
        )

        result: dict[str, Any] = {
            "topic_id": topic_id,
            "started_at": start_time.isoformat(),
            "config": config,
            "steps": {},
            "skipped": False,
            "cost_summary": {},
        }

        # Check if should skip
        if config.get("skip_reason"):
            result["skipped"] = True
            result["skip_reason"] = config["skip_reason"]
            logger.info(f"Skipping topic {topic_id}: {config['skip_reason']}")
            return result

        model_tier = config.get("model_tier", ModelTier.MEDIUM)
        logger.info(
            f"Processing topic {topic_id} with tier={model_tier}, "
            f"value={topic_value_score:.2f}"
        )

        # Run historian
        if config.get("run_historian"):
            result["steps"]["historian"] = await self._run_historian(
                topic_id, model_tier
            )
        else:
            result["steps"]["historian"] = {"skipped": True}

        # Run analyst
        if config.get("run_analyst"):
            result["steps"]["analyst"] = await self._run_analyst(
                topic_id, model_tier
            )
        else:
            result["steps"]["analyst"] = {"skipped": True}

        # Run writer
        if config.get("run_writer"):
            result["steps"]["writer"] = await self._run_writer(
                topic_id, model_tier, is_for_report
            )
        else:
            result["steps"]["writer"] = {"skipped": True}

        # Run reviewer
        if config.get("run_reviewer"):
            result["steps"]["reviewer"] = await self._run_reviewer(
                topic_id, model_tier
            )
        else:
            result["steps"]["reviewer"] = {"skipped": True}

        # Add cost summary
        result["completed_at"] = datetime.now(timezone.utc).isoformat()
        result["duration_seconds"] = (
            datetime.now(timezone.utc) - start_time
        ).total_seconds()
        result["cost_summary"] = self._get_step_costs(result["steps"])

        return result

    async def _run_historian(
        self,
        topic_id: int,
        model_tier: ModelTier,
    ) -> dict[str, Any]:
        """Run historian step.

        Args:
            topic_id: Topic ID.
            model_tier: Model tier to use.

        Returns:
            Step result.
        """
        model = self._pipeline_policy.get_model_for_step(
            "generate_timeline",
            {"model_tier": model_tier},
        )

        # Placeholder - would call actual historian agent
        return {
            "status": "success",
            "model": model,
            "estimated_tokens": 500,
        }

    async def _run_analyst(
        self,
        topic_id: int,
        model_tier: ModelTier,
    ) -> dict[str, Any]:
        """Run analyst step.

        Args:
            topic_id: Topic ID.
            model_tier: Model tier to use.

        Returns:
            Step result.
        """
        model = self._pipeline_policy.get_model_for_step(
            "analyze_importance",
            {"model_tier": model_tier},
        )

        return {
            "status": "success",
            "model": model,
            "estimated_tokens": 300,
        }

    async def _run_writer(
        self,
        topic_id: int,
        model_tier: ModelTier,
        is_for_report: bool,
    ) -> dict[str, Any]:
        """Run writer step.

        Args:
            topic_id: Topic ID.
            model_tier: Model tier to use.
            is_for_report: Whether for report.

        Returns:
            Step result.
        """
        # Writer always uses at least medium tier
        effective_tier = model_tier if model_tier != ModelTier.SMALL else ModelTier.MEDIUM
        if is_for_report:
            effective_tier = ModelTier.LARGE

        model = self._pipeline_policy.get_model_for_step(
            "write_copy",
            {"model_tier": effective_tier, "is_for_report": is_for_report},
        )

        return {
            "status": "success",
            "model": model,
            "estimated_tokens": 800,
        }

    async def _run_reviewer(
        self,
        topic_id: int,
        model_tier: ModelTier,
    ) -> dict[str, Any]:
        """Run reviewer step.

        Args:
            topic_id: Topic ID.
            model_tier: Model tier to use.

        Returns:
            Step result.
        """
        model = self._pipeline_policy.get_model_for_step(
            "review_copy",
            {"model_tier": model_tier},
        )

        return {
            "status": "success",
            "model": model,
            "estimated_tokens": 400,
        }

    def _get_step_costs(self, steps: dict[str, Any]) -> dict[str, Any]:
        """Calculate costs for steps.

        Args:
            steps: Step results.

        Returns:
            Cost summary.
        """
        total_tokens = 0
        for step_name, step_result in steps.items():
            if not step_result.get("skipped"):
                total_tokens += step_result.get("estimated_tokens", 0)

        # Rough cost estimate
        estimated_cost = total_tokens * 0.00001  # Simplified

        return {
            "total_tokens": total_tokens,
            "estimated_cost_usd": estimated_cost,
            "steps_run": sum(
                1 for s in steps.values() if not s.get("skipped")
            ),
            "steps_skipped": sum(
                1 for s in steps.values() if s.get("skipped")
            ),
        }

    async def process_batch(
        self,
        topics: list[dict[str, Any]],
        is_for_report: bool = False,
    ) -> list[dict[str, Any]]:
        """Process a batch of topics.

        Args:
            topics: List of topic dicts with id, value_score, etc.
            is_for_report: Whether for report.

        Returns:
            List of results.
        """
        results = []

        # Sort by value score descending
        sorted_topics = sorted(
            topics,
            key=lambda t: t.get("value_score", 0),
            reverse=True,
        )

        for topic in sorted_topics:
            result = await self.process_topic(
                topic_id=topic["id"],
                topic_value_score=topic.get("value_score", 0.5),
                topic_changed=topic.get("changed", True),
                last_historian_at=topic.get("last_historian_at"),
                last_writer_at=topic.get("last_writer_at"),
                is_for_report=is_for_report,
            )
            results.append(result)

        return results

    def get_cost_summary(self) -> dict[str, Any]:
        """Get overall cost summary.

        Returns:
            Cost summary from tracker.
        """
        return self._cost_tracker.get_summary()
