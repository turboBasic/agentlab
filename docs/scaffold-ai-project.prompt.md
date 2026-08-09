# Prompt — scaffold an agentic AI project (OpenRouter via Anthropic SDK)

Reusable Claude Code prompt for scaffolding a terminal coding agent in modern Python, talking to
OpenRouter through the Anthropic Messages format. Model IDs and endpoint behavior in the
"Verified facts" section were confirmed against the live OpenRouter API on 2026-08-09.

---

## Task

Scaffold a new agentic AI project from scratch in a fresh directory (ask me for the name and
path before creating anything). It is a terminal-based coding agent: I give it a task, it plans,
calls tools (read/write files, run shell commands) inside a working directory, and iterates
until done. Follow my global instructions in ~/.claude/CLAUDE.md throughout.

Per my "New projects: AI instructions first" rule: create `.editorconfig`, `.gitattributes`,
`.gitignore`, `mise.toml`, `.pre-commit-config.yaml`, then `docs/ai-instructions.md` +
`CLAUDE.md` + `.github/copilot-instructions.md` BEFORE writing any Python.

## Verified facts — do not re-derive, do not WebFetch to "check" these

I confirmed all of this against the live API. Trust it.

1. OpenRouter exposes an **Anthropic-native Messages endpoint**: `POST https://openrouter.ai/api/v1/messages`.
   It is NOT only the OpenAI-compatible `/chat/completions` path.
2. The official `anthropic` Python SDK works against it directly:

   ```python
   anthropic.AsyncAnthropic(
       base_url="https://openrouter.ai/api/v1",
       api_key=os.environ["OPENROUTER_API_KEY"],  # sent as x-api-key; OpenRouter accepts it
   )
   ```

3. Verified working through that endpoint, for BOTH DeepSeek and Anthropic models:
   - non-streaming `messages.create`
   - `stream=True` SSE (`message_start` / `content_block_start` / `content_block_delta`
     with `thinking_delta` + `text_delta` / `content_block_stop` / `message_delta` / `message_stop`)
   - tool use: returns `stop_reason: "tool_use"` and a `tool_use` block with parsed `input`
4. Model IDs are **namespaced** on OpenRouter — a bare `claude-opus-5` will 404. Use:

   | Purpose | OpenRouter model ID |
   |---|---|
   | Default / cheap+fast driver | `deepseek/deepseek-v4-flash` |
   | DeepSeek pinned snapshot | `deepseek/deepseek-v4-flash-0731` |
   | DeepSeek heavier tier | `deepseek/deepseek-v4-pro` |
   | Anthropic flagship | `anthropic/claude-opus-5` |
   | Anthropic balanced | `anthropic/claude-sonnet-5` |
   | Anthropic cheap | `anthropic/claude-haiku-4.5` |
   | Floating "latest" pointers | `~anthropic/claude-opus-latest`, `~anthropic/claude-sonnet-latest`, `~deepseek/deepseek-v4-flash-latest` |

5. DeepSeek V4 Flash **always emits a leading `thinking` block** with `signature: ""`.
   Anthropic models via OpenRouter do not, unless asked.
6. `usage` on the response includes OpenRouter extras (`cost`, `is_byok`,
   `output_tokens_details.thinking_tokens`) alongside the standard Anthropic fields.

## Non-negotiable design decisions

- **No agent framework.** Hand-rolled async tool-use loop against the raw `anthropic` SDK.
  Do NOT introduce LangChain, LangGraph, Pydantic AI, CrewAI, AutoGen, or similar.
- **One SDK, one wire format.** Everything speaks the Anthropic Messages format. Do NOT add the
  `openai` package or an OpenAI-compatible code path. OpenRouter is reached as an
  Anthropic-compatible endpoint via `base_url`, nothing more.
- **Client construction is isolated.** Only `providers/*` imports `anthropic`. The agent loop, the
  CLI, and the tools never do. New backends implement a `Provider` protocol.
- **Model IDs never appear as literals outside the registry.** One module owns the table from the
  fact list above, with a `ModelSpec` per entry (id, family, supports_tools, supports_thinking,
  context window, whether it's a floating alias). Never branch on `"deepseek" in model_id`
  scattered through the codebase — ask the registry.
- **Every filesystem write and every shell command passes through a permission gate** before
  executing. No tool bypasses it on a production path; only test fixtures may use a
  non-interactive auto-approve gate.
- **Secrets never live in files.** `OPENROUTER_API_KEY` is read from the environment via
  `pydantic-settings`. Provide `.env.template` with `op://` references only, and a
  `mise run dev` task that wraps the CLI in `op run --env-file=.env.template --`.
  Never write a literal key anywhere, including tests — use obviously fake values (`sk-test-...`).

## Tech stack

- Python 3.14, `src/<pkg>/` layout, `uv` for deps (`pyproject.toml` + `uv.lock`). Never `pip install`.
- mise pins Python, uv, and the 1Password CLI; mise tasks for `run`, `lint`, `typecheck`, `test`, `test-live`.
- CLI: Typer. Rendering: Rich, with live-streaming assistant output and tool-call panels.
- Models: Pydantic v2 for anything crossing a boundary (provider responses, tool params, tool
  results, persisted rows). Settings: pydantic-settings. No bare dicts for long-lived data.
- Persistence: SQLite via `aiosqlite` — sessions + message history, resumable.
- Logging: structured JSON to stderr so it never collides with Rich on stdout.
- Lint/format: ruff, wired through pre-commit. Type checking: pyright **strict**.
- Tests: pytest + pytest-asyncio. Unit tests mock the provider client. A small suite marked
  `@pytest.mark.live` makes real OpenRouter calls and is deselected by default.
- Modern Python only: `X | None` not `Optional`, builtin `dict`/`list`, no `__future__` imports,
  no `TYPE_CHECKING` guards unless genuinely needed for a cycle. Full type hints everywhere.
- Async-first: provider calls, tool execution, and storage are all `async def`. No blocking I/O
  in the loop.
- No docstrings or multi-line comment blocks. Comments only where the WHY is non-obvious.

## Structure

```text
src/<pkg>/
├── cli.py            # Typer entrypoint: one-shot task + interactive REPL, --model, --version
├── config.py         # pydantic-settings: api key, default model, workdir, permission mode
├── logging.py        # structured JSON logging
├── models.py         # ModelSpec registry — the ONLY place model IDs are written
├── providers/
│   ├── base.py       # Provider protocol: complete() + stream()
│   ├── openrouter.py # AsyncAnthropic with base_url override
│   └── registry.py   # name -> Provider; never branch on provider name elsewhere
├── agent/
│   ├── loop.py       # the hand-rolled tool-use loop
│   ├── messages.py   # Pydantic message/content-block models
│   └── session.py    # conversation state, token accounting, cost tracking
├── tools/
│   ├── base.py       # Tool protocol + JSON schema declaration
│   ├── permissions.py# the gate
│   ├── fs.py         # read_file, write_file, edit_file, glob, grep
│   └── shell.py      # run_command
├── storage/          # db.py + repository.py
└── ui/               # Rich console rendering for streamed output
tests/                # mirrors src/, plus tests/integration (live, opt-in)
```

## The tool-use loop — required behaviors

- Loop until `stop_reason == "end_turn"`; keep going while it is `"tool_use"`. Cap iterations
  (configurable, default ~25) and surface a clear message when the cap is hit.
- Append the **full `response.content`** back as the assistant turn — never just the extracted
  text. Return **all** `tool_result` blocks for a turn in a **single** user message, each with the
  matching `tool_use_id`.
- Execute independent tool calls **concurrently** (`asyncio.gather`), because a single assistant
  turn can contain multiple `tool_use` blocks.
- On tool failure, return a `tool_result` with `is_error: True` and a useful message. Never drop
  a `tool_result` — a missing one wedges the conversation.
- Parse `tool_use.input` as the already-decoded object the SDK gives you. Never string-match
  serialized JSON.
- Handle `stop_reason == "max_tokens"` distinctly from `"end_turn"`, and handle
  `"refusal"`/unknown values without crashing (check `stop_reason` before touching `content[0]`).
- **`thinking` blocks:** render them dimmed if the user passes `--show-thinking`, otherwise hide
  them. DeepSeek's have an empty `signature`. Decide and document a single replay policy for
  multi-turn (echo them back verbatim vs. strip them before resending) — and **verify your choice
  against the live API with a two-turn DeepSeek tool-use conversation** before declaring it done.
  Do not guess; this is the one behavior I could not pre-confirm for you.
- Stream by default. Use the SDK's stream context manager and `get_final_message()` so you get
  the accumulated message without hand-rolling event accumulation, while still rendering
  `text_delta`s live.
- Set `max_tokens` generously (streaming, so timeouts aren't the constraint) — ~16k, from config.
- **Do not** pass Anthropic-first-party-only parameters through OpenRouter unless you have
  verified them there: no `thinking={"type": "adaptive"}`, no `output_config`/`effort`, no
  `betas=[...]`, no `cache_control`, no server-side tools. Keep the request body to the portable
  core: `model`, `max_tokens`, `system`, `messages`, `tools`, `tool_choice`, `stream`. If you want
  any of the extras, probe the endpoint with curl first and only add what actually returns 200.
- Do NOT add retry/fallback/multi-model routing. Single model per session; the SDK's built-in
  retries are enough.

## Permission gate

Three modes from config/CLI: `ask` (interactive Rich prompt, default), `auto` (allow), `deny`.
Prompt shows the concrete action — for shell, the exact command; for writes, the path and a diff
for edits. Support "allow once" vs "allow for this session" per tool. Confine every filesystem
path to the configured working directory: resolve to canonical form and reject anything that
escapes it (`..`, symlinks, absolute paths outside root). Reject shell operator chaining unless
the user explicitly opted into it.

## Deliverable order

1. Ask me for project name/path. Scaffold config files + AI instructions docs first.
2. `models.py` registry, `providers/`, `config.py` — then a smoke script that hits OpenRouter
   with `deepseek/deepseek-v4-flash` and prints the response. Run it. Show me the output.
3. `tools/` + permission gate, with unit tests.
4. `agent/loop.py` + `ui/`, with mocked-provider tests for: plain reply, single tool call,
   parallel tool calls, tool error, max-iteration cap.
5. `storage/`, `cli.py`.
6. `tests/integration/` live suite (marked, deselected by default) covering DeepSeek and one
   Anthropic model: streaming, tool use, and the multi-turn thinking-block replay question above.

## Acceptance criteria

- `mise run lint`, `mise run typecheck` (pyright strict), and `mise run test` all pass. Fix lint
  errors as they appear; do not defer them.
- `mise run dev -- "create hello.py that prints hi and run it"` works end to end against
  `deepseek/deepseek-v4-flash`, prompting for permission before the write and before the shell run.
- Switching to `--model anthropic/claude-sonnet-5` works with zero code changes.
- `grep -rn "openai" src/` returns nothing. `grep -rn "deepseek/\|anthropic/claude"` returns hits
  only in `models.py` and tests.
- `git grep -iE "sk-or-|sk-ant-"` finds nothing outside obviously-fake test values.
- Report honestly at the end: what you verified by running vs. what is untested, and anything you
  had to leave out.
