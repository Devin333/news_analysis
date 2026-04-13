"""Reviewer Agent implementation.

The Reviewer Agent validates generated content against
source materials and quality standards.
"""

from typing import Any

from app.agents.base import AgentConfig, BaseAgent
from app.agents.reviewer.input_builder import ReviewerInputBuilder
from app.agents.reviewer.rubric import get_rubric
from app.agents.reviewer.schemas import ReviewerInput, ReviewerOutput
from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


class ReviewerAgent(BaseAgent[ReviewerOutput]):
    """Agent for reviewing generated content.

    Reviews content against source materials and quality rubrics.
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
    ) -> None:
        """Initialize the Reviewer Agent.

        Args:
            config: Agent configuration.
        """
        config = config or AgentConfig(
            max_steps=4,
            temperature=0.3,  # Lower temperature for consistent reviews
            enable_tools=False,
            prompt_version="v1",
        )
        super().__init__(config=config)
        self._input_builder = ReviewerInputBuilder()

    @property
    def name(self) -> str:
        """Unique name of the agent."""
        return "reviewer"

    @property
    def prompt_key(self) -> str:
        """Key for prompt template lookup."""
        return "reviewer"

    @property
    def output_schema(self) -> type[ReviewerOutput]:
        """Pydantic model class for structured output."""
        return ReviewerOutput

    def build_input(self, **kwargs: Any) -> str:
        """Build input message for the agent.

        Args:
            **kwargs: Should contain 'reviewer_input' (ReviewerInput).

        Returns:
            Formatted input message.
        """
        reviewer_input: ReviewerInput | None = kwargs.get("reviewer_input")

        if reviewer_input is None:
            raise ValueError("reviewer_input is required")

        # Build context string
        content_context = self._input_builder.build_prompt_context(reviewer_input)

        # Get rubric for this copy type
        rubric = get_rubric(reviewer_input.copy_type)
        rubric_text = rubric.to_prompt_text()

        return f"""Please review the following content against the source materials and rubric.

{content_context}

{rubric_text}

Review the content thoroughly and provide your assessment as a JSON object with:
- review_status: "approve", "revise", or "reject"
- issues: List of issues found
- missing_points: Important points that are missing
- unsupported_claims: Claims without evidence
- style_issues: Style problems
- revision_hints: Specific hints for revision
- review_summary: Brief summary
- confidence: Your confidence (0-1)

Be thorough but fair. Focus on factual accuracy first."""

    def build_tools(self) -> list:
        """Build tools available to the agent.

        Reviewer doesn't use tools.

        Returns:
            Empty list.
        """
        return []

    async def review(
        self,
        reviewer_input: ReviewerInput,
    ) -> tuple[ReviewerOutput | None, Any]:
        """Review content.

        Args:
            reviewer_input: Prepared input for review.

        Returns:
            Tuple of (ReviewerOutput or None, RunResult).
        """
        return await self.run_structured(reviewer_input=reviewer_input)
