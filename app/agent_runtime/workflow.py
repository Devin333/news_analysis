"""Agent Workflow definitions.

This module defines reusable workflows that orchestrate multiple agents
in sequence or parallel.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from app.bootstrap.logging import get_logger

if TYPE_CHECKING:
    from app.agents.analyst.schemas import AnalystOutput
    from app.agents.analyst.service import AnalystService
    from app.agents.historian.schemas import HistorianOutput
    from app.agents.historian.service import HistorianService

logger = get_logger(__name__)

T = TypeVar("T")


class WorkflowStatus(str, Enum):
    """Status of a workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some steps succeeded, some failed


@dataclass
class WorkflowStepResult(Generic[T]):
    """Result of a single workflow step."""

    step_name: str
    success: bool
    output: T | None = None
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowResult:
    """Result of a complete workflow execution."""

    workflow_name: str
    status: WorkflowStatus
    steps: list[WorkflowStepResult] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        """Total duration in milliseconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return sum(s.duration_ms for s in self.steps)

    @property
    def success(self) -> bool:
        """Whether the workflow completed successfully."""
        return self.status == WorkflowStatus.COMPLETED

    def get_step(self, name: str) -> WorkflowStepResult | None:
        """Get a step result by name."""
        for step in self.steps:
            if step.step_name == name:
                return step
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_name": self.workflow_name,
            "status": self.status.value,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "steps": [
                {
                    "step_name": s.step_name,
                    "success": s.success,
                    "error": s.error,
                    "duration_ms": s.duration_ms,
                }
                for s in self.steps
            ],
            "metadata": self.metadata,
        }


class BaseWorkflow:
    """Base class for workflows."""

    def __init__(self, name: str) -> None:
        """Initialize the workflow.

        Args:
            name: Workflow name.
        """
        self.name = name

    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """Execute the workflow.

        Args:
            **kwargs: Workflow-specific arguments.

        Returns:
            WorkflowResult with execution details.
        """
        raise NotImplementedError


class HistorianThenAnalystWorkflow(BaseWorkflow):
    """Workflow that runs Historian followed by Analyst.

    This is the primary workflow for topic enrichment:
    1. Run Historian to get historical context
    2. Pass Historian output to Analyst
    3. Analyst provides value judgement with historical awareness
    """

    def __init__(
        self,
        historian_service: "HistorianService",
        analyst_service: "AnalystService",
    ) -> None:
        """Initialize the workflow.

        Args:
            historian_service: Service for running Historian.
            analyst_service: Service for running Analyst.
        """
        super().__init__("historian_then_analyst")
        self._historian_service = historian_service
        self._analyst_service = analyst_service

    async def execute(
        self,
        topic_id: int,
        *,
        skip_historian: bool = False,
        skip_analyst: bool = False,
    ) -> WorkflowResult:
        """Execute the Historian → Analyst workflow.

        Args:
            topic_id: ID of the topic to process.
            skip_historian: Skip Historian step.
            skip_analyst: Skip Analyst step.

        Returns:
            WorkflowResult with both agent outputs.
        """
        result = WorkflowResult(
            workflow_name=self.name,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        result.metadata["topic_id"] = topic_id

        historian_output: "HistorianOutput | None" = None
        analyst_output: "AnalystOutput | None" = None

        # Step 1: Run Historian
        if not skip_historian:
            step_start = datetime.utcnow()
            try:
                historian_output, historian_meta = await self._historian_service.run_for_topic(
                    topic_id
                )
                step_duration = (datetime.utcnow() - step_start).total_seconds() * 1000

                if historian_output:
                    result.steps.append(
                        WorkflowStepResult(
                            step_name="historian",
                            success=True,
                            output=historian_output,
                            duration_ms=step_duration,
                            metadata=historian_meta or {},
                        )
                    )
                    logger.info(
                        f"Historian completed: status={historian_output.historical_status}"
                    )
                else:
                    result.steps.append(
                        WorkflowStepResult(
                            step_name="historian",
                            success=False,
                            error="Historian returned no output",
                            duration_ms=step_duration,
                        )
                    )
            except Exception as e:
                step_duration = (datetime.utcnow() - step_start).total_seconds() * 1000
                result.steps.append(
                    WorkflowStepResult(
                        step_name="historian",
                        success=False,
                        error=str(e),
                        duration_ms=step_duration,
                    )
                )
                logger.error(f"Historian failed: {e}")

        # Step 2: Run Analyst
        if not skip_analyst:
            step_start = datetime.utcnow()
            try:
                analyst_output, analyst_meta = await self._analyst_service.run_for_topic(
                    topic_id,
                    historian_output=historian_output,
                )
                step_duration = (datetime.utcnow() - step_start).total_seconds() * 1000

                if analyst_output:
                    result.steps.append(
                        WorkflowStepResult(
                            step_name="analyst",
                            success=True,
                            output=analyst_output,
                            duration_ms=step_duration,
                            metadata=analyst_meta or {},
                        )
                    )
                    logger.info(f"Analyst completed: trend={analyst_output.trend_stage}")
                else:
                    result.steps.append(
                        WorkflowStepResult(
                            step_name="analyst",
                            success=False,
                            error="Analyst returned no output",
                            duration_ms=step_duration,
                        )
                    )
            except Exception as e:
                step_duration = (datetime.utcnow() - step_start).total_seconds() * 1000
                result.steps.append(
                    WorkflowStepResult(
                        step_name="analyst",
                        success=False,
                        error=str(e),
                        duration_ms=step_duration,
                    )
                )
                logger.error(f"Analyst failed: {e}")

        # Determine final status
        result.completed_at = datetime.utcnow()
        successful_steps = sum(1 for s in result.steps if s.success)
        total_steps = len(result.steps)

        if successful_steps == total_steps and total_steps > 0:
            result.status = WorkflowStatus.COMPLETED
        elif successful_steps > 0:
            result.status = WorkflowStatus.PARTIAL
        else:
            result.status = WorkflowStatus.FAILED

        # Store outputs in metadata for easy access
        result.metadata["historian_output"] = historian_output
        result.metadata["analyst_output"] = analyst_output

        logger.info(
            f"Workflow {self.name} completed with status {result.status.value} "
            f"in {result.duration_ms:.1f}ms"
        )

        return result


class ParallelAgentWorkflow(BaseWorkflow):
    """Workflow that runs multiple agents in parallel.

    Useful when agents don't depend on each other's output.
    """

    def __init__(self, name: str = "parallel_agents") -> None:
        """Initialize the workflow.

        Args:
            name: Workflow name.
        """
        super().__init__(name)
        self._agents: list[tuple[str, Any]] = []

    def add_agent(self, name: str, agent_service: Any) -> "ParallelAgentWorkflow":
        """Add an agent to the workflow.

        Args:
            name: Step name for this agent.
            agent_service: Agent service to run.

        Returns:
            Self for chaining.
        """
        self._agents.append((name, agent_service))
        return self

    async def execute(self, topic_id: int, **kwargs: Any) -> WorkflowResult:
        """Execute all agents in parallel.

        Args:
            topic_id: ID of the topic to process.
            **kwargs: Additional arguments passed to agents.

        Returns:
            WorkflowResult with all agent outputs.
        """
        import asyncio

        result = WorkflowResult(
            workflow_name=self.name,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        result.metadata["topic_id"] = topic_id

        async def run_agent(name: str, service: Any) -> WorkflowStepResult:
            """Run a single agent."""
            step_start = datetime.utcnow()
            try:
                output, meta = await service.run_for_topic(topic_id, **kwargs)
                step_duration = (datetime.utcnow() - step_start).total_seconds() * 1000
                return WorkflowStepResult(
                    step_name=name,
                    success=output is not None,
                    output=output,
                    error=None if output else "Agent returned no output",
                    duration_ms=step_duration,
                    metadata=meta or {},
                )
            except Exception as e:
                step_duration = (datetime.utcnow() - step_start).total_seconds() * 1000
                return WorkflowStepResult(
                    step_name=name,
                    success=False,
                    error=str(e),
                    duration_ms=step_duration,
                )

        # Run all agents in parallel
        tasks = [run_agent(name, service) for name, service in self._agents]
        step_results = await asyncio.gather(*tasks)
        result.steps = list(step_results)

        # Determine final status
        result.completed_at = datetime.utcnow()
        successful_steps = sum(1 for s in result.steps if s.success)
        total_steps = len(result.steps)

        if successful_steps == total_steps and total_steps > 0:
            result.status = WorkflowStatus.COMPLETED
        elif successful_steps > 0:
            result.status = WorkflowStatus.PARTIAL
        else:
            result.status = WorkflowStatus.FAILED

        return result


# Factory functions for common workflows


def create_historian_analyst_workflow(
    historian_service: "HistorianService",
    analyst_service: "AnalystService",
) -> HistorianThenAnalystWorkflow:
    """Create a Historian → Analyst workflow.

    Args:
        historian_service: Historian service.
        analyst_service: Analyst service.

    Returns:
        Configured workflow.
    """
    return HistorianThenAnalystWorkflow(
        historian_service=historian_service,
        analyst_service=analyst_service,
    )


async def run_historian_then_analyst(
    topic_id: int,
    historian_service: "HistorianService",
    analyst_service: "AnalystService",
) -> WorkflowResult:
    """Convenience function to run Historian → Analyst workflow.

    Args:
        topic_id: Topic to process.
        historian_service: Historian service.
        analyst_service: Analyst service.

    Returns:
        WorkflowResult.
    """
    workflow = create_historian_analyst_workflow(historian_service, analyst_service)
    return await workflow.execute(topic_id)


class WriteThenReviewWorkflow(BaseWorkflow):
    """Workflow that runs Writer followed by Reviewer.

    This workflow generates content and then reviews it:
    1. Run Writer to generate copy
    2. Run Reviewer to validate the copy
    3. Return combined result with review status
    """

    def __init__(
        self,
        writer_service: Any,
        reviewer_service: Any,
    ) -> None:
        """Initialize the workflow.

        Args:
            writer_service: Service for running Writer.
            reviewer_service: Service for running Reviewer.
        """
        super().__init__("write_then_review")
        self._writer_service = writer_service
        self._reviewer_service = reviewer_service

    async def execute(
        self,
        topic_id: int,
        copy_type: str = "topic_intro",
        *,
        historian_output: dict | None = None,
        analyst_output: dict | None = None,
    ) -> WorkflowResult:
        """Execute the Writer → Reviewer workflow.

        Args:
            topic_id: ID of the topic to process.
            copy_type: Type of copy to generate.
            historian_output: Optional historian output.
            analyst_output: Optional analyst output.

        Returns:
            WorkflowResult with writer and reviewer outputs.
        """
        result = WorkflowResult(
            workflow_name=self.name,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        result.metadata["topic_id"] = topic_id
        result.metadata["copy_type"] = copy_type

        writer_output = None
        reviewer_output = None

        # Step 1: Run Writer
        step_start = datetime.utcnow()
        try:
            if copy_type == "feed_card":
                writer_output, writer_meta = await self._writer_service.write_feed_card(
                    topic_id,
                    historian_output=historian_output,
                    analyst_output=analyst_output,
                )
            elif copy_type == "topic_intro":
                writer_output, writer_meta = await self._writer_service.write_topic_intro(
                    topic_id,
                    historian_output=historian_output,
                    analyst_output=analyst_output,
                )
            elif copy_type == "trend_card":
                writer_output, writer_meta = await self._writer_service.write_trend_card(
                    topic_id,
                    historian_output=historian_output,
                    analyst_output=analyst_output,
                )
            else:
                writer_output = None
                writer_meta = {"error": f"Unknown copy type: {copy_type}"}

            step_duration = (datetime.utcnow() - step_start).total_seconds() * 1000

            if writer_output:
                result.steps.append(
                    WorkflowStepResult(
                        step_name="writer",
                        success=True,
                        output=writer_output,
                        duration_ms=step_duration,
                        metadata=writer_meta or {},
                    )
                )
            else:
                result.steps.append(
                    WorkflowStepResult(
                        step_name="writer",
                        success=False,
                        error="Writer returned no output",
                        duration_ms=step_duration,
                    )
                )
        except Exception as e:
            step_duration = (datetime.utcnow() - step_start).total_seconds() * 1000
            result.steps.append(
                WorkflowStepResult(
                    step_name="writer",
                    success=False,
                    error=str(e),
                    duration_ms=step_duration,
                )
            )

        # Step 2: Run Reviewer (only if writer succeeded)
        if writer_output:
            step_start = datetime.utcnow()
            try:
                copy_body = writer_output.model_dump() if hasattr(writer_output, "model_dump") else writer_output

                if copy_type == "feed_card":
                    reviewer_output, reviewer_meta = await self._reviewer_service.review_feed_card(
                        topic_id, copy_body,
                        historian_output=historian_output,
                        analyst_output=analyst_output,
                    )
                elif copy_type == "topic_intro":
                    reviewer_output, reviewer_meta = await self._reviewer_service.review_topic_intro(
                        topic_id, copy_body,
                        historian_output=historian_output,
                        analyst_output=analyst_output,
                    )
                elif copy_type == "trend_card":
                    reviewer_output, reviewer_meta = await self._reviewer_service.review_trend_card(
                        topic_id, copy_body,
                        historian_output=historian_output,
                        analyst_output=analyst_output,
                    )
                else:
                    reviewer_output = None
                    reviewer_meta = {}

                step_duration = (datetime.utcnow() - step_start).total_seconds() * 1000

                if reviewer_output:
                    result.steps.append(
                        WorkflowStepResult(
                            step_name="reviewer",
                            success=True,
                            output=reviewer_output,
                            duration_ms=step_duration,
                            metadata=reviewer_meta or {},
                        )
                    )
                else:
                    result.steps.append(
                        WorkflowStepResult(
                            step_name="reviewer",
                            success=False,
                            error="Reviewer returned no output",
                            duration_ms=step_duration,
                        )
                    )
            except Exception as e:
                step_duration = (datetime.utcnow() - step_start).total_seconds() * 1000
                result.steps.append(
                    WorkflowStepResult(
                        step_name="reviewer",
                        success=False,
                        error=str(e),
                        duration_ms=step_duration,
                    )
                )

        # Determine final status
        result.completed_at = datetime.utcnow()
        successful_steps = sum(1 for s in result.steps if s.success)
        total_steps = len(result.steps)

        if successful_steps == total_steps and total_steps > 0:
            result.status = WorkflowStatus.COMPLETED
        elif successful_steps > 0:
            result.status = WorkflowStatus.PARTIAL
        else:
            result.status = WorkflowStatus.FAILED

        result.metadata["writer_output"] = writer_output
        result.metadata["reviewer_output"] = reviewer_output
        if reviewer_output:
            result.metadata["review_status"] = reviewer_output.review_status

        return result


def create_write_review_workflow(
    writer_service: Any,
    reviewer_service: Any,
) -> WriteThenReviewWorkflow:
    """Create a Writer → Reviewer workflow."""
    return WriteThenReviewWorkflow(writer_service, reviewer_service)
