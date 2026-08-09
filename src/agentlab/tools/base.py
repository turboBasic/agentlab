from __future__ import annotations

from typing import Any, ClassVar, Protocol, runtime_checkable

from agentlab.types import ToolSpec


@runtime_checkable
class Tool(Protocol):
    name: str
    description: str
    parameters: ClassVar[dict[str, Any]]
    requires_confirmation: bool

    def describe_action(self, arguments: dict[str, Any]) -> str:
        """Human-readable summary of what a call will do, shown in the permission prompt."""
        ...

    async def run(self, arguments: dict[str, Any]) -> str: ...


def to_spec(tool: Tool) -> ToolSpec:
    return ToolSpec(name=tool.name, description=tool.description, parameters=tool.parameters)
