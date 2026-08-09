from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

from openai import AsyncOpenAI

from agentlab.providers.openrouter import OpenRouterProvider
from agentlab.types import TextDelta, ToolCallDelta, TurnComplete, UserMessage


def _chunk(
    content: str | None = None,
    finish_reason: str | None = None,
    tool_calls: list[Any] | None = None,
    usage: Any | None = None,
) -> SimpleNamespace:
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(delta=delta, finish_reason=finish_reason)
    return SimpleNamespace(choices=[choice], usage=usage)


def _tool_call_delta(
    index: int, id_: str | None = None, name: str | None = None, arguments: str | None = None
) -> SimpleNamespace:
    function = SimpleNamespace(name=name, arguments=arguments)
    return SimpleNamespace(index=index, id=id_, function=function)


async def _fake_stream(chunks: list[SimpleNamespace]) -> AsyncIterator[SimpleNamespace]:
    for chunk in chunks:
        yield chunk


def _provider_with_chunks(chunks: list[SimpleNamespace]) -> OpenRouterProvider:
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=AsyncMock(return_value=_fake_stream(chunks)))
        )
    )
    return OpenRouterProvider(client=cast(AsyncOpenAI, fake_client))


async def test_stream_yields_text_then_turn_complete() -> None:
    provider = _provider_with_chunks(
        [_chunk(content="Hello"), _chunk(content=" world", finish_reason="stop")]
    )

    events = [
        event
        async for event in provider.stream(
            messages=[UserMessage(content="hi")],
            tools=[],
            model="deepseek/deepseek-v4-flash-0731",
            max_tokens=100,
            temperature=0.0,
        )
    ]

    assert events[0] == TextDelta(text="Hello")
    assert events[1] == TextDelta(text=" world")
    final = events[-1]
    assert isinstance(final, TurnComplete)
    assert final.stop_reason == "end_turn"


async def test_stream_accumulates_tool_call_fragments() -> None:
    provider = _provider_with_chunks(
        [
            _chunk(
                tool_calls=[_tool_call_delta(0, id_="call_1", name="read_file", arguments='{"pa')]
            ),
            _chunk(
                tool_calls=[_tool_call_delta(0, arguments='th": "a.py"}')],
                finish_reason="tool_calls",
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
    assert tool_events[0].tool_call.name == "read_file"
    assert tool_events[0].tool_call.arguments == {"path": "a.py"}
    final = events[-1]
    assert isinstance(final, TurnComplete)
    assert final.stop_reason == "tool_use"
