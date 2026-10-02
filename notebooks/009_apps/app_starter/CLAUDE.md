# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Scope: this is a standalone MCP starter project at `notebooks/009_apps/app_starter/`, with its own `pyproject.toml` and `uv.lock`. The root `agentlab` `docs/ai-instructions.md` rules (mise tasks, pyright strict, provider abstraction) do not apply here.

## Commands

```bash
uv run main.py                                   # start the MCP server (stdio)
uv run pytest                                    # all tests
uv run pytest tests/test_document.py::TestBinaryDocumentToMarkdown::test_binary_document_to_markdown_with_docx   # single test
```

## Architecture

- `main.py` creates a `FastMCP("docs")` server and registers each tool with `mcp.tool()(fn)`. A new tool is a plain function in `tools/` plus one registration line here.
- `tools/` holds the tool functions (`math.add`, `document.*`). `binary_document_to_markdown` (wraps `markitdown`, bytes plus extension) is the core converter; `document_path_to_markdown` reads a file path and delegates to it, and is the registered tool.
- Tool parameters use `pydantic.Field(description=...)` as defaults; docstrings double as the tool description shown to the model (summary, details, when to use, examples).
- `tests/fixtures/` holds the sample `.docx`/`.pdf` used by the document tests.
- Imports are top-level (`from tools.math import add`), so run from this directory.
