from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console

from agentlab.agent.loop import AgentLoop
from agentlab.agent.session import Session
from agentlab.config import Settings
from agentlab.logging import configure_logging, get_logger
from agentlab.providers.registry import build_provider
from agentlab.storage.db import connect
from agentlab.storage.repository import SessionRepository
from agentlab.tools.base import Tool
from agentlab.tools.filesystem import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from agentlab.tools.permissions import AutoApprovePermissionGate, InteractivePermissionGate
from agentlab.tools.shell import RunShellTool
from agentlab.ui.console import render_turn

app = typer.Typer(add_completion=False, help="A terminal coding-assistant agent.")


def _build_tools(workdir: Path) -> dict[str, Tool]:
    tools: list[Tool] = [
        ReadFileTool(workdir),
        WriteFileTool(workdir),
        EditFileTool(workdir),
        ListDirTool(workdir),
        RunShellTool(workdir),
    ]
    return {tool.name: tool for tool in tools}


@app.command()
def run(
    task: str = typer.Argument(..., help="What should the agent do?"),
    session_id: str | None = typer.Option(None, "--session", help="Resume an existing session id."),
) -> None:
    """Run one agent turn against TASK."""
    settings = Settings()
    configure_logging()
    logger = get_logger("cli")
    console = Console()

    async def _run() -> None:
        connection = await connect(settings.db_path)
        try:
            repository = SessionRepository(connection)
            session = (
                await Session.resume(repository, session_id)
                if session_id
                else await Session.create(repository)
            )
            logger.info("session started", extra={"extra_fields": {"session_id": session.id}})
            console.print(f"[dim]session {session.id}[/dim]")

            provider = build_provider(settings)
            gate = (
                AutoApprovePermissionGate()
                if settings.auto_approve
                else InteractivePermissionGate(console)
            )
            loop = AgentLoop(
                provider=provider,
                tools=_build_tools(settings.workdir),
                permission_gate=gate,
                model=settings.model,
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
            )
            await render_turn(loop.run_turn(session, task), console)
        finally:
            await connection.close()

    try:
        asyncio.run(_run())
    except RuntimeError as exc:
        console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    app()
