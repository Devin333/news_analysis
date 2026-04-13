"""LLM client protocol definition."""

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    """Response from LLM completion."""

    content: str
    model: str | None = None
    usage: dict[str, int] = Field(default_factory=dict)
    finish_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMMessage(BaseModel):
    """Message for LLM conversation."""

    role: str
    content: str
    name: str | None = None


@runtime_checkable
class LLMClientProtocol(Protocol):
    """Protocol for LLM client implementations."""

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Complete a conversation.

        Args:
            messages: List of message dicts with role and content.
            model: Optional model override.
            temperature: Optional temperature override.
            max_tokens: Optional max tokens override.
            **kwargs: Additional provider-specific options.

        Returns:
            LLMResponse with completion.
        """
        ...

    async def complete_with_tools(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        *,
        model: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Complete with tool calling support.

        Args:
            messages: List of message dicts.
            tools: List of tool definitions.
            model: Optional model override.
            **kwargs: Additional options.

        Returns:
            LLMResponse with completion and tool calls.
        """
        ...
