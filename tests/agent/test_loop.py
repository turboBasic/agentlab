from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from agentlab.agent.loop import AgentLoop, ToolFinished, ToolStarted
from agentlab.agent.session import Session
from agentlab.storage.repository import SessionRepository
from agentlab.tools.permissions import AutoApprovePermissionGate
from agentlab.types import (
    Message,
    StreamEvent,
    TextDelta,
    ToolCall,
    ToolCallDelta,
    ToolSpec,
    TurnComplete,
    Usage,
)


class FakeProvider:
    def __init__(self, responses: list[list[StreamEvent]]) -> None:
        self._responses = responses
        self.call_count = 0

    async def stream(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncIterator[StreamEvent]:
        response = self._responses[self.call_count]
        self.call_count += 1
        for event in response:
            yield event


class FakeTool:
    name = "echo"
    description = "echo the given arguments"
    parameters: ClassVar[dict[str, Any]] = {"type": "object", "properties": {}, "required": []}
    requires_confirmation = False

    def describe_action(self, arguments: dict[str, Any]) -> str:
        return "echo"

    async def run(self, arguments: dict[str, Any]) -> str:
        return "echoed"


async def test_run_turn_without_tool_calls(repository: SessionRepository) -> None:
    session = await Session.create(repository)
    provider = FakeProvider(
        [[TextDelta(text="hello"), TurnComplete(stop_reason="end_turn", usage=Usage())]]
    )
    loop = AgentLoop(
        provider=provider,
        tools={},
        permission_gate=AutoApprovePermissionGate(),
        model="m",
        max_tokens=100,
        temperature=0.0,
    )

    events = [event async for event in loop.run_turn(session, "hi")]

    assert events == [TextDelta(text="hello")]
    assert provider.call_count == 1
    assert session.messages[-1].role == "assistant"


async def test_run_turn_executes_tool_and_continues(repository: SessionRepository) -> None:
    session = await Session.create(repository)
    provider = FakeProvider(
        [
            [
                ToolCallDelta(tool_call=ToolCall(id="1", name="echo", arguments={})),
                TurnComplete(stop_reason="tool_use", usage=Usage()),
            ],
            [TextDelta(text="done"), TurnComplete(stop_reason="end_turn", usage=Usage())],
        ]
    )
    loop = AgentLoop(
        provider=provider,
        tools={"echo": FakeTool()},
        permission_gate=AutoApprovePermissionGate(),
        model="m",
        max_tokens=100,
        temperature=0.0,
    )

    events = [event async for event in loop.run_turn(session, "do it")]

    assert any(isinstance(event, ToolStarted) for event in events)
    assert any(isinstance(event, ToolFinished) for event in events)
    assert events[-1] == TextDelta(text="done")
    assert provider.call_count == 2
