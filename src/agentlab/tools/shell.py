from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, ClassVar


class RunShellTool:
    name = "run_shell"
    description = (
        "Run a shell command in the working directory and return its combined stdout/stderr."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "timeout_seconds": {"type": "integer", "default": 120},
        },
        "required": ["command"],
    }
    requires_confirmation = True

    def __init__(self, workdir: Path) -> None:
        self._workdir = workdir

    def describe_action(self, arguments: dict[str, Any]) -> str:
        return f"run `{arguments['command']}`"

    async def run(self, arguments: dict[str, Any]) -> str:
        timeout = arguments.get("timeout_seconds", 120)
        process = await asyncio.create_subprocess_shell(
            arguments["command"],
            cwd=self._workdir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except TimeoutError:
            process.kill()
            raise RuntimeError(
                f"command timed out after {timeout}s: {arguments['command']}"
            ) from None

        output = stdout.decode(errors="replace")
        if process.returncode != 0:
            return f"[exit code {process.returncode}]\n{output}"
        return output
