# Prompt — scaffold an agentic AI project (Anthropic API learning lab)

Reusable Claude Code prompt for scaffolding a terminal coding agent in modern Python against the
Anthropic Messages API, with OpenRouter as an opt-in cheap/zero-cost backend.

**Companion file:** `docs/openrouter-verified-facts.md` holds the live-API observations this
prompt cites by fact number (confirmed 2026-08-09). This prompt is normative — every rule lives
here; that file is empirical and carries no rules. Read it first.

---

## Goal — read this first, it governs every trade-off below

**This is a learning lab. Its product is my understanding of the Anthropic API, not the agent.**

The code is a means to that end and is expected to be rewritten several times. When a decision
trades implementation elegance against exposure to real Anthropic API mechanics, **exposure
wins** — even when that means more code, more branches, or a less tidy abstraction.

### What that implies concretely

- **First-party Anthropic is the reference path.** Default to `api.anthropic.com` with real
  model IDs and no `base_url` override, so that caching, `output_config.effort`, task budgets,
  beta headers, and server-side tools are all actually reachable. OpenRouter is an opt-in
  backend for cheap iteration, never the default.
- **Never hide a wire shape behind a neutral abstraction.** The loop works in the SDK's own
  content blocks. Do NOT invent a provider-neutral message model — a flattened assistant turn
  (`content: str` plus a separate `tool_calls` list) cannot represent `thinking` blocks,
  `cache_control`, or compaction blocks, and papering over that defeats the entire point of the
  project. See "Non-negotiable design decisions" for what the abstraction is allowed to cover.
- **Capabilities are declared, not assumed.** Optional request parameters differ by model and by
  backend. A single set of "uniform params" sent everywhere is the bug class this project exists
  to understand — `temperature` alone is rejected outright on Opus 5 / Opus 4.8 / Opus 4.7 /
  Fable 5 and rejected non-default on Sonnet 5.
- **Verify against the live API; write down what you learn.** Behavior I cannot confirm from
  docs must be probed with a real call, and the finding recorded (see "Learning notes").
- **Stop-anywhere ladder.** Build in the order given in "Learning ladder". Every rung must leave
  the project working and useful on its own. Do not begin a rung you cannot finish — a
  half-implemented rung is worse than an absent one.

### Non-goals

Not building a product. Do not add multi-user support, a plugin system, config profiles,
telemetry backends, retry/fallback/multi-model routing, or any abstraction whose only
justification is a hypothetical future requirement.

### What is NOT negotiable despite this being a lab

Keep all of the following — each one is load-bearing *for the learning goal*, not ceremony:

- **The permission gate.** It is the only thing between a model and my filesystem, and it is
  where tool-call interception is learned.
- **pyright strict + ruff via pre-commit.** Strict typing against the SDK's block unions is
  itself a way to learn the response shape — the type checker enumerates what can come back.
- **SQLite session persistence.** Resumable sessions are what make multi-turn thinking-block
  replay testable at all; without stored turns there is nothing to re-send.
- **The live opt-in test suite.** Several questions on the ladder can only be settled against
  the real API.

## Task

Scaffold a new agentic AI project from scratch in a fresh directory (ask me for the name and
path before creating anything). It is a terminal-based coding agent: I give it a task, it plans,
calls tools (read/write files, run shell commands) inside a working directory, and iterates
until done. Follow my global instructions in ~/.claude/CLAUDE.md throughout.

Per my "New projects: AI instructions first" rule: create `.editorconfig`, `.gitattributes`,
`.gitignore`, `mise.toml`, `.pre-commit-config.yaml`, then `docs/ai-instructions.md` +
`CLAUDE.md` + `.github/copilot-instructions.md` BEFORE writing any Python.

Carry the Goal section above into `docs/ai-instructions.md` — condensed, but with the
"exposure wins", "no neutral message model", and "capabilities are declared" rules intact.

## Verified facts — read `openrouter-verified-facts.md` now, before anything else

**Read `docs/openrouter-verified-facts.md` in full before writing any code or making any design
decision. This is not optional and not a reference for later.** It holds eight numbered facts,
confirmed against the live OpenRouter API, that the rest of this prompt cites by number — the
Anthropic-native Messages endpoint, the SDK client shape, namespaced model IDs, and the
tool-use / streaming / thinking-block behavior of the free and cheap backends. It also lists what
is **not** yet verified.

Do not re-derive those facts and do not WebFetch to "check" them. If a fact turns out to be
wrong, say so explicitly and record the correction there — do not silently work around it.

That file is evidence only; it contains no rules. Every rule lives in this prompt.

## Backends and models

Three backends, in priority order. **First-party is the default and the reference.**

| # | Backend | `base_url` | Key | Default model | Role |
|---|---|---|---|---|---|
| 1 | Anthropic first-party | *(none — SDK default)* | `ANTHROPIC_API_KEY` | `claude-sonnet-5` | **Default.** Reference path; the only one where every ladder rung is reachable. |
| 2 | OpenRouter — free tier | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `poolside/laguna-s-2.1:free` | Zero-cost tool-loop iteration: plumbing, permission-gate, and cap work. |
| 3 | OpenRouter — paid | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `deepseek/deepseek-v4-flash` | Cheap non-Anthropic model that reliably emits `thinking` blocks (see fact 5). |

`claude-sonnet-5` is the default because it reaches every rung — adaptive thinking on by default,
the full `low`→`max` effort ladder, prompt caching, 1M context — at $3/$15 per MTok. Do NOT
default to Haiku 4.5: no `effort` parameter and 200K context puts several rungs out of reach.

**Backend 2 is the zero-cost iteration path.** Rungs 0–2 of the ladder are pure plumbing (loop
shape, `stop_reason` handling, iteration cap, permission gate, tool errors) and should be
developed against the free model so I burn no credits on mechanics — facts 7–8 confirm it does
tool use, multi-turn `tool_result` round trips, and streaming over the Messages endpoint. Free
`:free` variants are rate-limited and rotate on OpenRouter's side — treat it as an
experimentation backend, never as a default, and make sure a rate-limit response surfaces as a
clear error rather than a hang.

## Non-negotiable design decisions

- **No agent framework.** Hand-rolled async tool-use loop against the raw `anthropic` SDK.
  Do NOT introduce LangChain, LangGraph, Pydantic AI, CrewAI, AutoGen, or similar.
- **One SDK, one wire format.** Everything speaks the Anthropic Messages format. Do NOT add the
  `openai` package or an OpenAI-compatible code path. OpenRouter is reached as an
  Anthropic-compatible endpoint via `base_url`, nothing more.
- **The loop works in the SDK's content blocks — no neutral message model.** Append the full
  `response.content` back as the assistant turn and persist that shape. Do NOT define parallel
  Pydantic mirrors of `TextBlock` / `ThinkingBlock` / `ToolUseBlock`, and do NOT flatten an
  assistant turn to a text field plus a separate `tool_calls` list. Pydantic is mandatory for
  everything that is genuinely mine (config, tool params, tool results, persisted row
  envelopes) — just not as a re-encoding of the wire format.
- **Provider abstraction covers exactly two things: client construction and capability
  declaration.** Since all three backends speak Messages, there is no translation layer to
  write. A `Provider` supplies the configured `AsyncAnthropic` client plus a capability record
  (does this backend/model accept `cache_control`, `output_config.effort`, `task_budget`, beta
  headers, server-side tools, `thinking.display`?). The loop consults that record before adding
  an optional parameter. If you find yourself writing a `_to_provider_message()` function, the
  design has gone wrong — stop and re-read the Goal section.
- **Only `providers/*` imports `anthropic` for construction.** The loop receives a client; it
  never builds one and never reads config to decide which backend it is on. It may import
  `anthropic.types` for block types — that is the point of the previous two rules.
- **Model IDs never appear as literals outside the registry.** One module owns the tables from
  "Backends and models" above, with a `ModelSpec` per entry: id, backend, family, context
  window, max output, whether it's a floating alias, and the capability flags. Never branch on
  `"deepseek" in model_id` or `"claude" in model_id` scattered through the codebase — ask the
  registry. This module is where the `temperature` question below gets answered once.
- **`temperature` and other sampling params are per-model, not global.** `temperature`, `top_p`,
  and `top_k` are **rejected with a 400** on Opus 5 / Opus 4.8 / Opus 4.7 / Fable 5, and
  rejected when non-default on Sonnet 5. Never send them unconditionally. Either omit them
  entirely (preferred — steer with prompting) or gate them on a registry capability flag. A
  config field holding a default sampling value that is then always passed through is a bug, not
  a default.
- **Every filesystem write and every shell command passes through a permission gate** before
  executing. No tool bypasses it on a production path; only test fixtures may use a
  non-interactive auto-approve gate.
- **Secrets never live in files.** `ANTHROPIC_API_KEY` and `OPENROUTER_API_KEY` are read from the
  environment via `pydantic-settings`. Provide `.env.template` with `op://` references only, and
  a `mise run dev` task that wraps the CLI in `op run --env-file=.env.template --`.
  Never write a literal key anywhere, including tests — use obviously fake values (`sk-test-...`).

## Tech stack

- Python 3.14, `src/<pkg>/` layout, `uv` for deps (`pyproject.toml` + `uv.lock`). Never `pip install`.
- mise pins Python, uv, and the 1Password CLI; mise tasks for `run`, `lint`, `typecheck`, `test`, `test-live`.
- CLI: Typer. Rendering: Rich, with live-streaming assistant output and tool-call panels.
- Models: Pydantic v2 for config, tool params, tool results, and persisted row envelopes.
  Settings: pydantic-settings. No bare dicts for long-lived data. **Not** for re-encoding
  provider content blocks — see the design decisions above.
- Persistence: SQLite via `aiosqlite` — sessions + message history, resumable. Store assistant
  turns in a form that round-trips content blocks losslessly, including `thinking` blocks and
  their `signature` field (even when empty). Version the schema from the start; the ladder will
  change this shape.
- Logging: structured JSON to stderr so it never collides with Rich on stdout.
- Lint/format: ruff, wired through pre-commit. Type checking: pyright **strict**.
- Tests: pytest + pytest-asyncio. Unit tests mock the provider client. A small suite marked
  `@pytest.mark.live` makes real API calls and is deselected by default.
- Modern Python only: `X | None` not `Optional`, builtin `dict`/`list`, **no `__future__`
  imports** (Python 3.14 does not need them — do not add `from __future__ import annotations` to
  any module), no `TYPE_CHECKING` guards unless genuinely needed for a cycle. Full type hints
  everywhere.
- Async-first: provider calls, tool execution, and storage are all `async def`. No blocking I/O
  in the loop.
- **No docstrings, ever** — not module-level, not class-level, not function-level. The one
  exception is Typer command functions, where the docstring *is* the `--help` text.
- **Comments: WHY-only, and only at API boundaries.** My global rule is no comments; this project
  relaxes it in exactly one place — where a request or response shape is non-obvious and getting
  it wrong fails silently. Specifically allowed: thinking-block replay rules, empty `signature`
  handling, `stop_reason` branches, `cache_control` placement, capability gating of optional
  params. One or two lines, stating the constraint and ideally the consequence of violating it.
  Everywhere else the global rule stands: no comments.

## Learning notes — `docs/api-notes.md`

Maintain `docs/api-notes.md` **in the new project** as a running record of what was actually
learned. This file is a **primary deliverable**, not documentation-after-the-fact.

Do not confuse it with the companion facts file: `openrouter-verified-facts.md` is a pre-existing
**input** covering OpenRouter behavior I already probed, and is not yours to rewrite (only to
correct, if you disprove a fact). `api-notes.md` is an **output** you create and grow — chiefly
about first-party Anthropic behavior, which the facts file does not cover.

Structure it as dated entries, newest first, each with:

- **Claim** — the behavior, in one line.
- **How verified** — live call / SDK source / docs, with the model and backend named.
- **Surprise** — what differed from what you expected going in. Omit if nothing did.
- **Open question** — what remains unknown, if anything.

Rules:

- One entry per ladder rung, minimum. Add entries mid-rung whenever a live call contradicts an
  assumption.
- Record **negative** findings too: params rejected, endpoints that 404'd, blocks silently
  dropped. Those are the most valuable entries and the easiest to lose.
- Never write an entry claiming live verification for something that was not actually run.
  Mark inference as inference.

## Structure

```text
src/<pkg>/
├── cli.py            # Typer entrypoint: one-shot task + interactive REPL, --model, --backend,
│                     #   --show-thinking, --effort, --version
├── config.py         # pydantic-settings: keys per backend, default model, workdir,
│                     #   permission mode, max_tokens, iteration cap. NO global temperature.
├── logging.py        # structured JSON logging
├── models.py         # ModelSpec registry — the ONLY place model IDs are written; owns the
│                     #   capability flags the loop gates optional params on
├── providers/
│   ├── base.py       # Provider protocol: client construction + capability record. NOT a
│   │                 #   message translation layer.
│   ├── anthropic.py  # first-party AsyncAnthropic (default, no base_url)
│   ├── openrouter.py # AsyncAnthropic with base_url override (free + paid model sets)
│   └── registry.py   # name -> Provider; never branch on provider name elsewhere
├── agent/
│   ├── loop.py       # the hand-rolled tool-use loop
│   └── session.py    # conversation state (SDK content blocks), token + cost accounting
├── tools/
│   ├── base.py       # Tool protocol + JSON schema declaration
│   ├── permissions.py# the gate
│   ├── fs.py         # read_file, write_file, edit_file, glob, grep
│   └── shell.py      # run_command
├── storage/          # db.py + repository.py (lossless content-block round-trip, versioned)
└── ui/               # Rich console rendering for streamed output + thinking display
docs/api-notes.md     # running record of verified API behavior — a primary deliverable
tests/                # mirrors src/, plus tests/integration (live, opt-in)
```

There is deliberately no module for message or content-block models: conversation state holds
the SDK's content blocks directly, so there is nothing for such a module to contain.

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
  serialized JSON. Treat `tool_use.id` as an opaque token — never validate or pattern-match its
  format (fact 7: OpenRouter-proxied models return `chatcmpl-tool-…`, not `toolu_…`).
- An assistant turn can contain **zero text blocks** — thinking-only turns are real (fact 8).
  Never assume `content[0]` is text, and never derive the assistant turn by extracting text.
- Handle `stop_reason == "max_tokens"` distinctly from `"end_turn"`, and handle
  `"refusal"`/unknown values without crashing (check `stop_reason` before touching `content[0]`).
- **`thinking` blocks:** render them dimmed if the user passes `--show-thinking`, otherwise hide
  them. DeepSeek's have an empty `signature`. The replay rule is a hard API requirement, not a
  style choice: **thinking blocks must be echoed back unchanged when continuing on the same
  model** — read but never edit or reconstruct them; a modified block is rejected. Blocks replayed
  to a *different* model are dropped from the prompt rather than rendered. Empty-text blocks
  still get echoed verbatim. **Verify this against the live API with a two-turn tool-use
  conversation on both a Claude model and DeepSeek** before declaring the rung done, and record
  the finding in `docs/api-notes.md`. Do not guess.
- Stream by default. Use the SDK's stream context manager and `get_final_message()` so you get
  the accumulated message without hand-rolling event accumulation, while still rendering
  `text_delta`s live. Do NOT build an index-keyed dict accumulator over raw SSE events — if you
  are concatenating `partial_json` fragments by hand, you are reimplementing the SDK.
- Set `max_tokens` generously (streaming, so timeouts aren't the constraint) — ~16k, from config.
  Remember `max_tokens` caps **thinking plus response text together**: a value tuned for a
  thinking-off model will truncate mid-answer once thinking is on.
- **Never send an optional parameter a backend hasn't been verified to accept.** The portable core
  is `model`, `max_tokens`, `system`, `messages`, `tools`, `tool_choice`, `stream`. Anything
  beyond that is gated on a registry capability flag — check the facts file (numbered facts for
  what is confirmed, "Known unverified" for what is not), probe with curl if it is unlisted, set
  the flag, then use it. This is the mechanism, not a one-off: adding an ungated param anywhere
  is the bug class from the Goal section.
- Do NOT add retry/fallback/multi-model routing. Single model per session; the SDK's built-in
  retries are enough.

## Permission gate

Three modes from config/CLI: `ask` (interactive Rich prompt, default), `auto` (allow), `deny`.
Prompt shows the concrete action — for shell, the exact command; for writes, the path and a diff
for edits. Support "allow once" vs "allow for this session" per tool. Confine every filesystem
path to the configured working directory: resolve to canonical form and reject anything that
escapes it (`..`, symlinks, absolute paths outside root). Reject shell operator chaining unless
the user explicitly opted into it.

## Learning ladder — build in this order, stop anywhere

Each rung must leave the project **working, runnable, and useful on its own**, with lint,
typecheck, and tests green, and at least one `docs/api-notes.md` entry. Do not start a rung you
cannot finish. Stop and report after each rung rather than running ahead — I may want to stop, or
change direction, at any boundary.

Every rung below states three things. **Depends on** lists what is *additionally* load-bearing for
that rung — re-read it before starting; a rung built without it will be subtly wrong even if it
runs. **Deliver** is the scope. **Done when** is the falsifiable check: if you cannot demonstrate
it, the rung is not finished, regardless of how much code exists.

**Five sections govern every rung and are never repeated in a `Depends on` list:** Goal, Verified
facts, Non-negotiable design decisions, Tech stack, and Learning notes. They are in force
continuously — a `Depends on` field that omits them is not permission to ignore them. If a rung's
implementation would violate one of those five to satisfy its own `Deliver`, the five win: stop
and tell me, rather than working around the rule.

### Rung 0 — foundation

- **Depends on:** Task · facts 1, 2, 4 · Backends and models · Structure
- **Deliver:** Ask me for project name/path. Config files + AI instructions docs (including the
  condensed Goal section). Then `models.py` registry, `providers/`, `config.py`, and a smoke
  script that hits first-party `claude-sonnet-5` and prints the response.
- **Done when:** the smoke script prints a real response on first-party `claude-sonnet-5`, and
  the same script prints one via `--backend openrouter` on the free model — both shown to me,
  before any loop code exists.

### Rung 1 — the loop, correct

Develop against the **free OpenRouter backend** so no credits go to mechanics. This is where
everything that is *not* Anthropic-specific gets settled; all of it is part of this rung, not a
follow-up.

- **Depends on:** facts 7, 8 · The tool-use loop — required behaviors (all of it) · Permission
  gate · Structure
- **Deliver:** `tools/` + permission gate with unit tests; `agent/loop.py` + `ui/`; `storage/`;
  `cli.py`. Specifically:
  - Append the full `response.content` as the assistant turn; return **all** `tool_result` blocks
    for a turn in a **single** user message.
  - Execute independent tool calls concurrently with `asyncio.gather` — permission prompts still
    serialize, execution does not.
  - Configurable iteration cap (~25 default) with a clear surfaced message when hit.
  - `stop_reason` handled exhaustively: `end_turn`, `tool_use`, `max_tokens` distinctly, and
    `refusal`/unknown without crashing. Check `stop_reason` before touching `content[0]`.
  - Survive an assistant turn with zero text blocks (fact 8) — thinking-only turns are real.
  - A real system prompt: role, working directory, tool guidance.
- **Done when:** `"create hello.py that prints hi and run it"` completes end to end on both
  backends, prompting before the write and before the shell run; and mocked-provider tests cover
  plain reply, single tool call, parallel tool calls, tool error, max-iteration cap, and
  `max_tokens` truncation.

### Rung 2 — thinking blocks and multi-turn replay

First rung with live tests.

- **Depends on:** facts 5, 8 · The tool-use loop (the `thinking` bullet — the replay rule is an
  API requirement, not a style choice) · the Tech stack persistence rule specifically: blocks must
  round-trip losslessly, empty `signature` included
- **Deliver:** `--show-thinking` rendering (dimmed, hidden by default); persistence that
  round-trips thinking blocks byte-for-byte; the replay policy exercised across turns.
- **Done when:** a two-turn tool-use conversation replays stored thinking blocks without a 400,
  demonstrated live on both a Claude model and a thinking-emitting OpenRouter model, and the
  result — including what happens when blocks are replayed to a *different* model — is recorded
  in `api-notes.md`.

### Rung 3 — usage and cost accounting

- **Depends on:** fact 6 (OpenRouter extras are absent from the SDK's typed `usage` — reading
  them needs an untyped access)
- **Deliver:** read `usage` per turn, accumulate across the session, surface it in the UI.
  Include `cost` and `output_tokens_details.thinking_tokens` where present.
- **Done when:** a multi-turn session reports a running token total, and a cost figure on any
  backend that supplies one.

### Rung 4 — prompt caching

The main cost lever in an agent loop, and the rung where the prefix-match invariant gets learned
the hard way. First-party only.

- **Depends on:** facts file → "Known unverified" (whether OpenRouter honors `cache_control` is
  untested; if you probe it, record the result there) · **rung 3**, since the check below is a
  `usage` reading — attempting this rung first leaves you no way to tell whether it worked
- **Deliver:** `cache_control` placement on the system prompt and tool definitions.
- **Done when:** `cache_read_input_tokens` is demonstrably non-zero on a second turn — a zero
  reading means it is not working, however plausible the placement looks.

### Rung 5 — effort and task budgets

- **Depends on:** facts file → "Known unverified" — `effort` and `task_budget` are
  first-party-confirmed only, so both need a capability flag before use
- **Deliver:** `output_config.effort` exposed as `--effort`; `task_budget` for the agentic loop.
- **Done when:** the same task run at two effort levels shows a measured difference in tool-call
  count or turn length, recorded in `api-notes.md`.

### Rung 6 — long conversations

- **Depends on:** **rung 1**'s full-`response.content` rule (compaction requires appending the
  blocks, not just their text) · the Tech stack schema-versioning rule, since this rung changes
  the persisted shape
- **Deliver:** compaction and/or context editing.
- **Done when:** a conversation long enough to trigger the mechanism continues coherently, with
  the returned compaction blocks preserved on the following turn.

## Acceptance criteria

Per rung: its own "Done when" check, plus lint, typecheck (pyright strict), tests green, and a
`docs/api-notes.md` entry.

The following are **standing invariants** — they must hold at the end of every rung from rung 1
onward, not just once:

- `mise run lint`, `mise run typecheck` (pyright strict), and `mise run test` all pass. Fix lint
  errors as they appear; do not defer them.
- The end-to-end run from rung 1's "Done when" still works on **both** backends with zero code
  changes between them. A later rung that breaks the cheap backend has regressed, even if its own
  check passes.
- `grep -rn "openai" src/` returns nothing.
- `grep -rn "from __future__" src/` returns nothing.
- `grep -rn "claude-\|deepseek/\|poolside/" src/` returns hits only in `models.py`.
- No module-, class-, or function-level docstrings anywhere except Typer command functions.
- No local mirror of a provider message or content-block type, and no function that translates
  between one and a provider message type.
- `grep -rn "temperature" src/` shows it either absent or gated on a registry capability flag —
  never unconditionally passed.
- `git grep -iE "sk-or-|sk-ant-"` finds nothing outside obviously-fake test values.
- Live suite stays **cheap and narrow**: small `max_tokens`, few calls, run manually via
  `mise run test-live`, never in CI, never in `mise run ci`.

**Report honestly at the end of every rung:** what you verified by running versus what is
inferred or untested, which probes failed, and anything you left out. An unverified claim in
`docs/api-notes.md` is worse than no entry — this project's whole output is knowing what is
actually true.
