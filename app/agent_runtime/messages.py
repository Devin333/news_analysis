"""Agent runtime message models."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class BaseMessage(BaseModel):
    """Base message in agent runtime."""

    role: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SystemMessage(BaseMessage):
    role: Literal["system"] = "system"


class UserMessage(BaseMessage):
    role: Literal["user"] = "user"


class AssistantMessage(BaseMessage):
    role: Literal["assistant"] = "assistant"


class ToolMessage(BaseMessage):
    role: Literal["tool"] = "tool"
    tool_name: str


class ObservationMessage(BaseMessage):
    role: Literal["observation"] = "observation"
