"""Prompts module for prompt template management."""

from app.prompts.registry import (
    PromptRegistry,
    get_registry,
    get_prompt,
    register_prompt,
)

__all__ = [
    "PromptRegistry",
    "get_registry",
    "get_prompt",
    "register_prompt",
]
