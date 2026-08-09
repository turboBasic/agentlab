from __future__ import annotations

from collections.abc import AsyncIterator

from rich.console import Console

from agentlab.agent.loop import LoopEvent, ToolFinished, ToolStarted
from agentlab.types import TextDelta


async def render_turn(events: AsyncIterator[LoopEvent], console: Console) -> None:
    in_text = False
    async for event in events:
        if isinstance(event, TextDelta):
            console.print(event.text, end="")
            in_text = True
            continue

        if in_text:
            console.print()
            in_text = False

        if isinstance(event, ToolStarted):
            console.print(f"[cyan]->[/cyan] {event.action}")
        elif isinstance(event, ToolFinished):
            style = "red" if event.is_error else "green"
            mark = "x" if event.is_error else "v"
            console.print(f"[{style}]{mark}[/{style}] {event.tool_name}: {_truncate(event.result)}")
        else:
            console.print(f"[red]x denied:[/red] {event.tool_name}")

    if in_text:
        console.print()


def _truncate(text: str, limit: int = 200) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."
