from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Literal

from openai import AsyncOpenAI, omit
from openai.types.chat import (
    ChatCompletionFunctionToolParam,
    ChatCompletionMessageFunctionToolCallParam,
    ChatCompletionMessageParam,
    ChatCompletionToolUnionParam,
)
from openai.types.shared_params import FunctionDefinition

from agentlab.types import (
    Message,
    StreamEvent,
    SystemMessage,
    TextDelta,
    ToolCall,
    ToolCallDelta,
    ToolMessage,
    ToolSpec,
    TurnComplete,
    Usage,
    UserMessage,
)

_APP_HEADERS = {"HTTP-Referer": "https://github.com/agentlab", "X-Title": "agentlab"}

StopReason = Literal["end_turn", "tool_use", "max_tokens"]

_FINISH_REASON_MAP: dict[str, StopReason] = {
    "stop": "end_turn",
    "tool_calls": "tool_use",
    "length": "max_tokens",
}


class OpenRouterProvider:
    def __init__(
        self,
        *,
        api_key: str = "",
        base_url: str = "https://openrouter.ai/api/v1",
        client: AsyncOpenAI | None = None,
    ) -> None:
        self._client = client or AsyncOpenAI(
            api_key=api_key, base_url=base_url, default_headers=_APP_HEADERS
        )

    async def stream(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncIterator[StreamEvent]:
        raw_stream = await self._client.chat.completions.create(
            model=model,
            messages=[_to_openai_message(m) for m in messages],
            tools=[_to_openai_tool(t) for t in tools] or omit,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            stream_options={"include_usage": True},
        )

        pending_tool_calls: dict[int, dict[str, str]] = {}
        stop_reason: StopReason = "end_turn"
        usage = Usage()

        async for chunk in raw_stream:
            if chunk.usage is not None:
                usage = Usage(
                    input_tokens=chunk.usage.prompt_tokens,
                    output_tokens=chunk.usage.completion_tokens,
                )
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta
            if delta.content:
                yield TextDelta(text=delta.content)
            for tool_call_delta in delta.tool_calls or []:
                slot = pending_tool_calls.setdefault(
                    tool_call_delta.index, {"id": "", "name": "", "arguments": ""}
                )
                if tool_call_delta.id:
                    slot["id"] = tool_call_delta.id
                function = tool_call_delta.function
                if function is not None and function.name:
                    slot["name"] = function.name
                if function is not None and function.arguments:
                    slot["arguments"] += function.arguments
            if choice.finish_reason:
                stop_reason = _FINISH_REASON_MAP.get(choice.finish_reason, "end_turn")

        for slot in pending_tool_calls.values():
            yield ToolCallDelta(
                tool_call=ToolCall(
                    id=slot["id"],
                    name=slot["name"],
                    arguments=json.loads(slot["arguments"]) if slot["arguments"] else {},
                )
            )

        yield TurnComplete(stop_reason=stop_reason, usage=usage)


def _to_openai_tool(tool: ToolSpec) -> ChatCompletionToolUnionParam:
    function: FunctionDefinition = {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.parameters,
    }
    return ChatCompletionFunctionToolParam(type="function", function=function)


def _to_openai_message(message: Message) -> ChatCompletionMessageParam:
    if isinstance(message, SystemMessage):
        return {"role": "system", "content": message.content}
    if isinstance(message, UserMessage):
        return {"role": "user", "content": message.content}
    if isinstance(message, ToolMessage):
        return {"role": "tool", "tool_call_id": message.tool_call_id, "content": message.content}
    tool_calls: list[ChatCompletionMessageFunctionToolCallParam] = [
        {
            "id": call.id,
            "type": "function",
            "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
        }
        for call in message.tool_calls
    ]
    if tool_calls:
        return {"role": "assistant", "content": message.content or None, "tool_calls": tool_calls}
    return {"role": "assistant", "content": message.content or None}
