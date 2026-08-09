from __future__ import annotations

from pathlib import Path

from agentlab.tools.shell import RunShellTool


async def test_run_shell_returns_stdout(tmp_path: Path) -> None:
    tool = RunShellTool(tmp_path)

    output = await tool.run({"command": "echo hi"})

    assert output.strip() == "hi"


async def test_run_shell_reports_nonzero_exit(tmp_path: Path) -> None:
    tool = RunShellTool(tmp_path)

    output = await tool.run({"command": "exit 7"})

    assert "[exit code 7]" in output
