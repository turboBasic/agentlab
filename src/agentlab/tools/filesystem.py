from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, ClassVar


class PathEscapesWorkdirError(Exception):
    pass


def _resolve(workdir: Path, path: str) -> Path:
    resolved = (workdir / path).resolve()
    if not resolved.is_relative_to(workdir.resolve()):
        raise PathEscapesWorkdirError(f"{path!r} resolves outside the working directory")
    return resolved


class ReadFileTool:
    name = "read_file"
    description = (
        "Read the full contents of a text file, given a path relative to the working directory."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }
    requires_confirmation = False

    def __init__(self, workdir: Path) -> None:
        self._workdir = workdir

    def describe_action(self, arguments: dict[str, Any]) -> str:
        return f"read {arguments['path']}"

    async def run(self, arguments: dict[str, Any]) -> str:
        path = _resolve(self._workdir, arguments["path"])
        return await asyncio.to_thread(path.read_text)


class WriteFileTool:
    name = "write_file"
    description = (
        "Write text content to a file, given a path relative to the working directory. "
        "Overwrites the file if it exists, creates it (and parent directories) otherwise."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
        "required": ["path", "content"],
    }
    requires_confirmation = True

    def __init__(self, workdir: Path) -> None:
        self._workdir = workdir

    def describe_action(self, arguments: dict[str, Any]) -> str:
        return f"write {arguments['path']}"

    async def run(self, arguments: dict[str, Any]) -> str:
        path = _resolve(self._workdir, arguments["path"])
        content = arguments["content"]

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

        await asyncio.to_thread(_write)
        return f"wrote {len(content)} bytes to {arguments['path']}"


class ListDirTool:
    name = "list_dir"
    description = (
        "List entries in a directory, given a path relative to the working directory "
        "('.' for the working directory itself)."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"path": {"type": "string", "default": "."}},
        "required": [],
    }
    requires_confirmation = False

    def __init__(self, workdir: Path) -> None:
        self._workdir = workdir

    def describe_action(self, arguments: dict[str, Any]) -> str:
        return f"list {arguments.get('path', '.')}"

    async def run(self, arguments: dict[str, Any]) -> str:
        path = _resolve(self._workdir, arguments.get("path", "."))

        def _list() -> list[str]:
            return sorted(p.name + ("/" if p.is_dir() else "") for p in path.iterdir())

        entries = await asyncio.to_thread(_list)
        return "\n".join(entries) if entries else "(empty)"


class EditFileTool:
    name = "edit_file"
    description = (
        "Replace an exact occurrence of `old_text` with `new_text` in a file, given a path "
        "relative to the working directory. Fails if `old_text` is not found exactly once."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old_text": {"type": "string"},
            "new_text": {"type": "string"},
        },
        "required": ["path", "old_text", "new_text"],
    }
    requires_confirmation = True

    def __init__(self, workdir: Path) -> None:
        self._workdir = workdir

    def describe_action(self, arguments: dict[str, Any]) -> str:
        return f"edit {arguments['path']}"

    async def run(self, arguments: dict[str, Any]) -> str:
        path = _resolve(self._workdir, arguments["path"])
        old_text = arguments["old_text"]
        new_text = arguments["new_text"]

        def _edit() -> None:
            text = path.read_text()
            count = text.count(old_text)
            if count == 0:
                raise ValueError(f"old_text not found in {arguments['path']}")
            if count > 1:
                raise ValueError(
                    f"old_text found {count} times in {arguments['path']}; must be unique"
                )
            path.write_text(text.replace(old_text, new_text, 1))

        await asyncio.to_thread(_edit)
        return f"edited {arguments['path']}"
