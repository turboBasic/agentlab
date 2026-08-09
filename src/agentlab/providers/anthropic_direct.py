from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Literal

from anthropic import AsyncAnthropic, omit
from anthropic.types import (
    MessageParam,
    TextBlockParam,
    ToolParam,
    ToolResultBlockParam,
    ToolUseBlockParam,
)

from agentlab.types import (
    AssistantMessage,
    Message,
    StreamEvent,
    SystemMessage,
    TextDelta,
    ToolCall,
    ToolCallDelta,
    ToolSpec,
    TurnComplete,
    Usage,
    UserMessage,
)

StopReason = Literal["end_turn", "tool_use", "max_tokens"]

_STOP_REASON_MAP: dict[str, StopReason] = {
    "end_turn": "end_turn",
    "stop_sequence": "end_turn",
    "tool_use": "tool_use",
    "max_tokens": "max_tokens",
}


class AnthropicProvider:
    def __init__(self, *, api_key: str = "", client: AsyncAnthropic | None = None) -> None:
        self._client = client or AsyncAnthropic(api_key=api_key)

    async def stream(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncIterator[StreamEvent]:
        system, anthropic_messages = _to_anthropic_messages(messages)
        anthropic_tools: list[ToolParam] = [
            ToolParam(name=tool.name, description=tool.description, input_schema=tool.parameters)
            for tool in tools
        ]

        raw_stream = await self._client.messages.create(
            model=model,
            system=system or omit,
            messages=anthropic_messages,
            tools=anthropic_tools or omit,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )

        pending_tool_blocks: dict[int, dict[str, str]] = {}
        stop_reason: StopReason = "end_turn"
        usage = Usage()

        async for event in raw_stream:
            if event.type == "message_start":
                usage = Usage(input_tokens=event.message.usage.input_tokens)
            elif event.type == "content_block_start" and event.content_block.type == "tool_use":
                pending_tool_blocks[event.index] = {
                    "id": event.content_block.id,
                    "name": event.content_block.name,
                    "json": "",
                }
            elif event.type == "content_block_delta":
                if event.delta.type == "text_delta":
                    yield TextDelta(text=event.delta.text)
                elif event.delta.type == "input_json_delta":
                    pending_tool_blocks[event.index]["json"] += event.delta.partial_json
            elif event.type == "message_delta":
                if event.delta.stop_reason:
                    stop_reason = _STOP_REASON_MAP.get(event.delta.stop_reason, "end_turn")
                usage = Usage(
                    input_tokens=usage.input_tokens,
                    output_tokens=event.usage.output_tokens,
                )

        for block in pending_tool_blocks.values():
            yield ToolCallDelta(
                tool_call=ToolCall(
                    id=block["id"],
                    name=block["name"],
                    arguments=json.loads(block["json"]) if block["json"] else {},
                )
            )

        yield TurnComplete(stop_reason=stop_reason, usage=usage)


def _to_anthropic_messages(messages: list[Message]) -> tuple[str, list[MessageParam]]:
    system_parts: list[str] = []
    anthropic_messages: list[MessageParam] = []
    pending_tool_results: list[ToolResultBlockParam] = []

    def flush_tool_results() -> None:
        if pending_tool_results:
            anthropic_messages.append(MessageParam(role="user", content=list(pending_tool_results)))
            pending_tool_results.clear()

    for message in messages:
        if isinstance(message, SystemMessage):
            system_parts.append(message.content)
        elif isinstance(message, UserMessage):
            flush_tool_results()
            anthropic_messages.append(MessageParam(role="user", content=message.content))
        elif isinstance(message, AssistantMessage):
            flush_tool_results()
            blocks: list[TextBlockParam | ToolUseBlockParam] = []
            if message.content:
                blocks.append(TextBlockParam(type="text", text=message.content))
            blocks.extend(
                ToolUseBlockParam(type="tool_use", id=call.id, name=call.name, input=call.arguments)
                for call in message.tool_calls
            )
            anthropic_messages.append(MessageParam(role="assistant", content=blocks))
        else:
            pending_tool_results.append(
                ToolResultBlockParam(
                    type="tool_result",
                    tool_use_id=message.tool_call_id,
                    content=message.content,
                    is_error=message.is_error,
                )
            )

    flush_tool_results()
    return "\n".join(system_parts), anthropic_messages
