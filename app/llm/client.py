"""LLM client implementation.

This module provides a unified LLM client that supports multiple providers.
"""

from dataclasses import dataclass
from typing import Any

from app.bootstrap.logging import get_logger
from app.bootstrap.settings import get_settings
from app.contracts.protocols.llm import LLMResponse

logger = get_logger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM client."""

    provider: str = "openai"
    model: str = "gpt-4"
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: float = 60.0


class LLMClient:
    """Unified LLM client supporting multiple providers.

    Currently supports:
    - OpenAI (and compatible APIs)
    - Mock (for testing)
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        """Initialize the client.

        Args:
            config: LLM configuration.
        """
        self._config = config or self._load_config()
        self._client: Any = None

    def _load_config(self) -> LLMConfig:
        """Load config from settings."""
        settings = get_settings()
        return LLMConfig(
            provider=settings.llm_provider,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )

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
            **kwargs: Additional options.

        Returns:
            LLMResponse with completion.
        """
        model = model or self._config.model
        temperature = temperature if temperature is not None else self._config.temperature
        max_tokens = max_tokens or self._config.max_tokens

        if self._config.provider == "mock":
            return await self._mock_complete(messages)

        if self._config.provider in ("openai", "azure"):
            return await self._openai_complete(
                messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

        raise ValueError(f"Unsupported provider: {self._config.provider}")

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
        model = model or self._config.model

        if self._config.provider == "mock":
            return await self._mock_complete(messages)

        if self._config.provider in ("openai", "azure"):
            return await self._openai_complete_with_tools(
                messages,
                tools,
                model=model,
                **kwargs,
            )

        raise ValueError(f"Unsupported provider: {self._config.provider}")

    async def _openai_complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs: Any,
    ) -> LLMResponse:
        """Complete using OpenAI API."""
        try:
            import openai

            if self._client is None:
                self._client = openai.AsyncOpenAI(
                    api_key=self._config.api_key,
                    base_url=self._config.base_url,
                    timeout=self._config.timeout,
                )

            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            choice = response.choices[0]
            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                usage=usage,
                finish_reason=choice.finish_reason,
            )

        except ImportError:
            logger.error("openai package not installed")
            raise
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def _openai_complete_with_tools(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        *,
        model: str,
        **kwargs: Any,
    ) -> LLMResponse:
        """Complete with tools using OpenAI API."""
        try:
            import openai

            if self._client is None:
                self._client = openai.AsyncOpenAI(
                    api_key=self._config.api_key,
                    base_url=self._config.base_url,
                    timeout=self._config.timeout,
                )

            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                **kwargs,
            )

            choice = response.choices[0]
            content = choice.message.content or ""

            # Handle tool calls
            if choice.message.tool_calls:
                import json
                tool_calls_str = []
                for tc in choice.message.tool_calls:
                    tool_calls_str.append(
                        json.dumps({
                            "tool": tc.function.name,
                            "arguments": json.loads(tc.function.arguments),
                        })
                    )
                content = "\n".join(tool_calls_str)

            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return LLMResponse(
                content=content,
                model=response.model,
                usage=usage,
                finish_reason=choice.finish_reason,
            )

        except ImportError:
            logger.error("openai package not installed")
            raise
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def _mock_complete(
        self,
        messages: list[dict[str, str]],
    ) -> LLMResponse:
        """Mock completion for testing."""
        # Return a simple mock response
        last_message = messages[-1]["content"] if messages else ""

        return LLMResponse(
            content=f"Mock response to: {last_message[:50]}...",
            model="mock",
            usage={"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
            finish_reason="stop",
        )


# Singleton instance
_default_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get the default LLM client.

    Returns:
        The default LLMClient instance.
    """
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
