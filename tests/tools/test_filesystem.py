from __future__ import annotations

from pathlib import Path

import pytest

from agentlab.tools.filesystem import (
    EditFileTool,
    ListDirTool,
    PathEscapesWorkdirError,
    ReadFileTool,
    WriteFileTool,
)


async def test_write_then_read_roundtrip(tmp_path: Path) -> None:
    write = WriteFileTool(tmp_path)
    read = ReadFileTool(tmp_path)

    await write.run({"path": "a.txt", "content": "hello"})

    assert await read.run({"path": "a.txt"}) == "hello"


async def test_edit_file_replaces_unique_occurrence(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    edit = EditFileTool(tmp_path)

    await edit.run({"path": "a.py", "old_text": "x = 1", "new_text": "x = 2"})

    assert (tmp_path / "a.py").read_text() == "x = 2\n"


async def test_edit_file_rejects_non_unique_occurrence(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\nx = 1\n")
    edit = EditFileTool(tmp_path)

    with pytest.raises(ValueError, match="found 2 times"):
        await edit.run({"path": "a.py", "old_text": "x = 1", "new_text": "x = 2"})


async def test_list_dir(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("")
    (tmp_path / "sub").mkdir()
    list_dir = ListDirTool(tmp_path)

    result = await list_dir.run({"path": "."})

    assert "a.txt" in result
    assert "sub/" in result


async def test_read_file_rejects_path_escape(tmp_path: Path) -> None:
    read = ReadFileTool(tmp_path)

    with pytest.raises(PathEscapesWorkdirError):
        await read.run({"path": "../../etc/passwd"})
