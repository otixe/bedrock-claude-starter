"""Pydantic models for messages, tools, and memory entries."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class TextBlock(BaseModel):
    """Plain text content."""

    model_config = ConfigDict(frozen=True)
    type: Literal["text"] = "text"
    text: str


class ToolUseBlock(BaseModel):
    """Claude requested a tool call."""

    model_config = ConfigDict(frozen=True)
    type: Literal["tool_use"] = "tool_use"
    tool_use_id: str
    name: str
    input: dict[str, Any]


class ToolResultBlock(BaseModel):
    """Result of running a tool, sent back to Claude."""

    model_config = ConfigDict(frozen=True)
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str
    is_error: bool = False


ContentBlock = TextBlock | ToolUseBlock | ToolResultBlock


class Message(BaseModel):
    """A single conversation turn."""

    model_config = ConfigDict(frozen=True)
    role: Literal["user", "assistant"]
    content: list[ContentBlock]


class ToolDefinition(BaseModel):
    """Schema describing a tool to Claude."""

    model_config = ConfigDict(frozen=True)
    name: str
    description: str
    input_schema: dict[str, Any]


class MemoryEntry(BaseModel):
    """Something the agent should remember."""

    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Final response from `agent.run(...)`."""

    text: str
    iterations: int
    tool_calls: list[ToolUseBlock] = Field(default_factory=list)
    stop_reason: str = ""
