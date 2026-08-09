from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from pydantic import BaseModel

from agentlab.agent.session import Session
from agentlab.providers.base import Provider
from agentlab.tools.base import Tool, to_spec
from agentlab.tools.permissions import PermissionGate
from agentlab.types import (
    AssistantMessage,
    TextDelta,
    ToolCall,
    ToolCallDelta,
    ToolMessage,
    UserMessage,
)


class ToolStarted(BaseModel):
    tool_name: str
    action: str


class ToolFinished(BaseModel):
    tool_name: str
    result: str
    is_error: bool


class ToolDenied(BaseModel):
    tool_name: str


LoopEvent = TextDelta | ToolStarted | ToolFinished | ToolDenied


@dataclass
class AgentLoop:
    provider: Provider
    tools: dict[str, Tool]
    permission_gate: PermissionGate
    model: str
    max_tokens: int
    temperature: float

    async def run_turn(self, session: Session, user_input: str) -> AsyncIterator[LoopEvent]:
        await session.append(UserMessage(content=user_input))
        tool_specs = [to_spec(tool) for tool in self.tools.values()]

        while True:
            assistant_text = ""
            pending_tool_calls: list[ToolCall] = []

            async for event in self.provider.stream(
                messages=session.messages,
                tools=tool_specs,
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            ):
                if isinstance(event, TextDelta):
                    assistant_text += event.text
                    yield event
                elif isinstance(event, ToolCallDelta):
                    pending_tool_calls.append(event.tool_call)

            await session.append(
                AssistantMessage(content=assistant_text, tool_calls=pending_tool_calls)
            )

            if not pending_tool_calls:
                return

            for call in pending_tool_calls:
                async for tool_event in self._execute_tool(session, call):
                    yield tool_event

    async def _execute_tool(self, session: Session, call: ToolCall) -> AsyncIterator[LoopEvent]:
        tool = self.tools.get(call.name)
        if tool is None:
            message = ToolMessage(
                tool_call_id=call.id, content=f"unknown tool: {call.name}", is_error=True
            )
            await session.append(message)
            yield ToolFinished(tool_name=call.name, result=message.content, is_error=True)
            return

        action = tool.describe_action(call.arguments)
        if tool.requires_confirmation:
            yield ToolStarted(tool_name=tool.name, action=action)
            if not await self.permission_gate.confirm(action=action):
                await session.append(
                    ToolMessage(tool_call_id=call.id, content="denied by user", is_error=True)
                )
                yield ToolDenied(tool_name=tool.name)
                return
        else:
            yield ToolStarted(tool_name=tool.name, action=action)

        try:
            output = await tool.run(call.arguments)
            is_error = False
        except Exception as exc:  # tool failures are reported to the model, not raised
            output = f"{type(exc).__name__}: {exc}"
            is_error = True

        await session.append(ToolMessage(tool_call_id=call.id, content=output, is_error=is_error))
        yield ToolFinished(tool_name=tool.name, result=output, is_error=is_error)
