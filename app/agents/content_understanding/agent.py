"""ContentUnderstandingAgent implementation."""

from typing import Any

from app.agents.base import BaseAgent, AgentConfig
from app.agents.content_understanding.schemas import ContentUnderstandingOutput
from app.contracts.dto.normalized_item import NormalizedItemDTO


class ContentUnderstandingAgent(BaseAgent[ContentUnderstandingOutput]):
    """Agent for understanding and analyzing content.

    Analyzes normalized items to extract:
    - Content type classification
    - Board type classification
    - Key points
    - Importance score
    - Candidate entities
    - Significance summary
    """

    @property
    def name(self) -> str:
        return "ContentUnderstandingAgent"

    @property
    def prompt_key(self) -> str:
        return "content_understanding"

    @property
    def output_schema(self) -> type[ContentUnderstandingOutput]:
        return ContentUnderstandingOutput

    def build_input(self, **kwargs: Any) -> str:
        """Build input from normalized item.

        Args:
            item: NormalizedItemDTO to analyze.

        Returns:
            Formatted input message.
        """
        item: NormalizedItemDTO | None = kwargs.get("item")

        if item is None:
            # Build from individual fields
            title = kwargs.get("title", "")
            excerpt = kwargs.get("excerpt", "")
            clean_text = kwargs.get("clean_text", "")
            source_type = kwargs.get("source_type", "unknown")
        else:
            title = item.title
            excerpt = item.excerpt or ""
            clean_text = item.clean_text or ""
            source_type = "unknown"

        # Truncate clean_text if too long
        if len(clean_text) > 2000:
            clean_text = clean_text[:2000] + "..."

        input_parts = [
            f"Title: {title}",
            f"Source Type: {source_type}",
        ]

        if excerpt:
            input_parts.append(f"Excerpt: {excerpt}")

        if clean_text:
            input_parts.append(f"Content:\n{clean_text}")

        return "\n\n".join(input_parts)

    async def analyze_item(
        self,
        item: NormalizedItemDTO,
    ) -> tuple[ContentUnderstandingOutput | None, Any]:
        """Analyze a normalized item.

        Convenience method for running the agent on an item.

        Args:
            item: The item to analyze.

        Returns:
            Tuple of (parsed output or None, run result).
        """
        return await self.run_structured(item=item)
