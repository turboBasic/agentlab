from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from agentlab.types import Message, StreamEvent, ToolSpec


class Provider(Protocol):
    """A model backend that turns a conversation + tool specs into a stream of events.

    Implementations translate `agentlab.types` messages to/from their own wire format;
    callers (the agent loop) never see provider-specific shapes.
    """

    def stream(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncIterator[StreamEvent]: ...
