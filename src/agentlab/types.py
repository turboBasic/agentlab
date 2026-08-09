"""Provider-agnostic conversation and streaming types shared by `providers/` and `agent/`."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class SystemMessage(BaseModel):
    role: Literal["system"] = "system"
    content: str


class UserMessage(BaseModel):
    role: Literal["user"] = "user"
    content: str


class AssistantMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list[ToolCall])


class ToolMessage(BaseModel):
    role: Literal["tool"] = "tool"
    tool_call_id: str
    content: str
    is_error: bool = False


Message = Annotated[
    SystemMessage | UserMessage | AssistantMessage | ToolMessage,
    Field(discriminator="role"),
]


class TextDelta(BaseModel):
    type: Literal["text_delta"] = "text_delta"
    text: str


class ToolCallDelta(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    tool_call: ToolCall


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class TurnComplete(BaseModel):
    type: Literal["turn_complete"] = "turn_complete"
    stop_reason: Literal["end_turn", "tool_use", "max_tokens"]
    usage: Usage


StreamEvent = Annotated[TextDelta | ToolCallDelta | TurnComplete, Field(discriminator="type")]
