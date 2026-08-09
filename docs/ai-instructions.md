# AI Instructions — agentlab

Single source of truth for all AI coding tools (Claude Code, GitHub Copilot) working in
this repo. `CLAUDE.md` and `.github/copilot-instructions.md` both point here.

## Project overview

`agentlab` is a terminal coding-assistant agent. A user gives it a task; it plans, calls
tools (read/write files, run shell commands) inside a working directory, and iterates
until done. The model backing it is swappable between OpenRouter (default) and direct
Anthropic API through a provider abstraction — no framework, a hand-rolled async
tool-use loop.

Non-negotiable design decisions (do not silently change these):

- **No agent framework.** The tool-use loop in `agent/loop.py` is hand-rolled against
  the raw `openai`/`anthropic` SDKs. Do not introduce LangGraph, Pydantic AI, or similar
  without being asked.
- **Provider abstraction is mandatory.** Application code (the loop, the CLI) never
  imports `openai` or `anthropic` directly — only `providers/*` does. New providers
  implement the `Provider` protocol in `providers/base.py`.
- **Every filesystem write and shell command passes through the permission gate**
  (`tools/permissions.py`) before executing. No tool bypasses this in production code
  paths; only test fixtures use the non-interactive gate.
- **Secrets never live in files.** `OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY` are read
  from the environment (`config.py`, via `pydantic-settings`) and are expected to be
  injected by `op run --env-file=.env.template` (see `mise run run`). Never add a
  literal API key anywhere, including tests and examples.

## Tech stack

- **Language:** Python 3.14, `src/agentlab/` layout.
- **Tool version management:** mise (`mise.toml`) — Python, uv, 1Password CLI.
- **Dependency management:** uv (`pyproject.toml` + `uv.lock`). Never `pip install`.
- **CLI framework:** Typer, rendered with Rich (live-streaming output).
- **Data models:** Pydantic v2. **Settings:** `pydantic-settings`.
- **Model providers:** `openai` SDK against OpenRouter's OpenAI-compatible endpoint
  (default path), `anthropic` SDK for direct Anthropic access — both behind
  `providers/base.py:Provider`.
- **Persistence:** SQLite via `aiosqlite` for session/message history
  (`storage/db.py`, `storage/repository.py`).
- **Logging:** structured JSON logging only (`logging.py`), no tracing backend wired
  in yet.
- **Linting/formatting:** ruff (lint + format), enforced via pre-commit.
- **Type checking:** pyright, strict mode.
- **Testing:** pytest + pytest-asyncio. Unit tests mock provider clients; a small opt-in
  suite marked `@pytest.mark.live` makes real API calls and is excluded by default
  (`mise run test-live` to run it).
- **Secrets:** 1Password CLI (`op run --env-file=.env.template -- ...`), never `.env`
  files with real values.

## Project structure

```text
.
├── mise.toml                  # tool versions + dev tasks
├── pyproject.toml             # deps, ruff, pyright, pytest config
├── .env.template              # op:// secret references for `op run`
├── docs/ai-instructions.md    # this file — authoritative AI instructions
├── src/agentlab/
│   ├── cli.py                 # Typer entrypoint
│   ├── config.py              # pydantic-settings: provider/model/keys
│   ├── logging.py             # structured JSON logging setup
│   ├── providers/             # Provider protocol + OpenRouter/Anthropic adapters
│   ├── agent/                 # tool-use loop, message models, session state
│   ├── tools/                 # filesystem/shell tools + permission gate
│   ├── storage/               # SQLite session/message persistence
│   └── ui/                    # Rich console rendering for streaming output
└── tests/                     # mirrors src/, plus tests/integration (live, opt-in)
```

Keep this tree current — update it in the same change that adds/removes a top-level
module under `src/agentlab/`.

## Code generation rules

- Async-first: provider calls, tool execution, and storage are all `async def`. Don't
  introduce blocking I/O in the agent loop.
- Full type hints everywhere; pyright strict must pass (`mise run typecheck`).
- New tools implement the `Tool` protocol in `tools/base.py` and declare their JSON
  schema there — don't hand-roll ad hoc dict schemas in the loop.
- New providers implement `providers/base.py:Provider` and are registered in
  `providers/registry.py`; never branch on provider name outside the registry.
- Pydantic models for all structured data crossing a boundary (provider responses,
  tool results, persisted rows). Avoid bare dicts for anything long-lived.
- No comments unless the WHY is non-obvious. No docstrings/multi-line comment blocks.
- Don't add retry/fallback/multi-model logic unless asked — the provider layer is
  intentionally single-model right now.

## AI behavior guidelines

- Before adding a dependency, check whether `openai`, `anthropic`, `pydantic`, `typer`,
  or `rich` already cover the need.
- Run `mise run lint`, `mise run typecheck`, and `mise run test` before considering
  Python changes complete.
- When changing provider request/response handling, update both `providers/openrouter.py`
  and `providers/anthropic_direct.py` if the change is provider-agnostic — the two must
  stay behaviorally equivalent from the loop's point of view.
- Never commit real secrets to `.env.template`, tests, or fixtures — use obviously fake
  values (`sk-test-...`) in tests.
