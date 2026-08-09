from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

from anthropic import AsyncAnthropic

from agentlab.providers.anthropic_direct import AnthropicProvider
from agentlab.types import (
    AssistantMessage,
    SystemMessage,
    TextDelta,
    ToolCall,
    ToolCallDelta,
    ToolMessage,
    TurnComplete,
    UserMessage,
)


async def _fake_stream(events: list[SimpleNamespace]) -> AsyncIterator[SimpleNamespace]:
    for event in events:
        yield event


def _provider_with_events(events: list[SimpleNamespace]) -> tuple[AnthropicProvider, AsyncMock]:
    create_mock = AsyncMock(return_value=_fake_stream(events))
    fake_client = SimpleNamespace(messages=SimpleNamespace(create=create_mock))
    return AnthropicProvider(client=cast(AsyncAnthropic, fake_client)), create_mock


async def test_stream_yields_text_then_turn_complete() -> None:
    provider, _ = _provider_with_events(
        [
            SimpleNamespace(
                type="message_start",
                message=SimpleNamespace(usage=SimpleNamespace(input_tokens=10)),
            ),
            SimpleNamespace(
                type="content_block_start", index=0, content_block=SimpleNamespace(type="text")
            ),
            SimpleNamespace(
                type="content_block_delta",
                index=0,
                delta=SimpleNamespace(type="text_delta", text="Hi"),
            ),
            SimpleNamespace(
                type="message_delta",
                delta=SimpleNamespace(stop_reason="end_turn"),
                usage=SimpleNamespace(output_tokens=5),
            ),
        ]
    )

    events = [
        event
        async for event in provider.stream(
            messages=[UserMessage(content="hi")],
            tools=[],
            model="claude-sonnet-4-5-20250929",
            max_tokens=100,
            temperature=0.0,
        )
    ]

    assert events[0] == TextDelta(text="Hi")
    final = events[-1]
    assert isinstance(final, TurnComplete)
    assert final.stop_reason == "end_turn"
    assert final.usage.input_tokens == 10
    assert final.usage.output_tokens == 5


async def test_stream_accumulates_tool_use_block() -> None:
    provider, _ = _provider_with_events(
        [
            SimpleNamespace(
                type="message_start", message=SimpleNamespace(usage=SimpleNamespace(input_tokens=1))
            ),
            SimpleNamespace(
                type="content_block_start",
                index=0,
                content_block=SimpleNamespace(type="tool_use", id="call_1", name="read_file"),
            ),
            SimpleNamespace(
                type="content_block_delta",
                index=0,
                delta=SimpleNamespace(type="input_json_delta", partial_json='{"path": "a.py"}'),
            ),
            SimpleNamespace(
                type="message_delta",
                delta=SimpleNamespace(stop_reason="tool_use"),
                usage=SimpleNamespace(output_tokens=3),
            ),
        ]
    )

    events = [
        event
        async for event in provider.stream(
            messages=[UserMessage(content="read a.py")],
            tools=[],
            model="m",
            max_tokens=100,
            temperature=0.0,
        )
    ]

    tool_events = [event for event in events if isinstance(event, ToolCallDelta)]
    assert len(tool_events) == 1
    assert tool_events[0].tool_call.arguments == {"path": "a.py"}
    final = events[-1]
    assert isinstance(final, TurnComplete)
    assert final.stop_reason == "tool_use"


async def test_stream_groups_consecutive_tool_results_into_one_message() -> None:
    provider, create_mock = _provider_with_events(
        [
            SimpleNamespace(
                type="message_delta",
                delta=SimpleNamespace(stop_reason="end_turn"),
                usage=SimpleNamespace(output_tokens=0),
            )
        ]
    )
    messages = [
        SystemMessage(content="be helpful"),
        UserMessage(content="do two things"),
        AssistantMessage(
            content="",
            tool_calls=[
                ToolCall(id="1", name="a", arguments={}),
                ToolCall(id="2", name="b", arguments={}),
            ],
        ),
        ToolMessage(tool_call_id="1", content="a done"),
        ToolMessage(tool_call_id="2", content="b done"),
    ]

    async for _ in provider.stream(
        messages=messages, tools=[], model="m", max_tokens=10, temperature=0.0
    ):
        pass

    sent: Mapping[str, Any] = create_mock.call_args.kwargs
    assert sent["system"] == "be helpful"
    assert sent["messages"][-1]["role"] == "user"
    assert len(sent["messages"][-1]["content"]) == 2
    assert sent["messages"][-1]["content"][0]["tool_use_id"] == "1"
    assert sent["messages"][-1]["content"][1]["tool_use_id"] == "2"
