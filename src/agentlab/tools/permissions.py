from __future__ import annotations

import asyncio
from typing import Protocol

from rich.console import Console
from rich.prompt import Confirm


class PermissionGate(Protocol):
    async def confirm(self, *, action: str) -> bool: ...


class InteractivePermissionGate:
    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console(stderr=True)

    async def confirm(self, *, action: str) -> bool:
        self._console.print(f"[yellow]agentlab wants to:[/yellow] {action}")
        return await asyncio.to_thread(Confirm.ask, "Allow?", default=False, console=self._console)


class AutoApprovePermissionGate:
    """Non-interactive gate — only for tests or an explicit `Settings.auto_approve` opt-in."""

    async def confirm(self, *, action: str) -> bool:
        return True
