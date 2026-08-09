# agentlab

A terminal coding-assistant agent. Give it a task; it reads/edits files and runs shell
commands in your working directory via a hand-rolled tool-use loop, backed by a
swappable model provider (OpenRouter by default, direct Anthropic API as an
alternative).

See [`docs/ai-instructions.md`](docs/ai-instructions.md) for the full architecture and
conventions.

## Prerequisites

- [mise](https://mise.jdx.dev) — manages Python, uv, and the 1Password CLI for this repo.
- A [1Password](https://1password.com) account with `op` signed in (`op signin`), and
  items holding your OpenRouter / Anthropic API keys.

## Setup

```bash
mise install          # installs python, uv, 1password-cli per mise.toml
mise run setup         # uv sync + pre-commit install
```

Edit `.env.template` so the `op://` references point at your actual 1Password vault,
item, and field names.

## Running

```bash
mise run run "fix the failing test in src/foo.py"
```

This resolves secrets with `op run --env-file=.env.template` and invokes the CLI —
no real secret ever touches disk.

## Development

```bash
mise run fmt         # ruff format
mise run lint        # ruff check
mise run typecheck   # pyright --strict
mise run test        # pytest (mocked providers, excludes live tests)
mise run test-live   # opt-in tests against real provider APIs
mise run ci          # lint + typecheck + test
```

## Switching providers

Default provider is OpenRouter. To use direct Anthropic instead, set in your
environment (or `.env.template`):

```bash
AGENTLAB_PROVIDER=anthropic
AGENTLAB_MODEL=claude-sonnet-4-5-20250929   # a real Anthropic model id
```

The default model shipped in `config.py` is an OpenRouter-only slug
(`deepseek/deepseek-v4-flash-0731`), so it has no direct-Anthropic equivalent — switching
`AGENTLAB_PROVIDER` to `anthropic` requires also setting `AGENTLAB_MODEL` to a Claude
model id.

## Free OpenRouter model option

OpenRouter also hosts zero-cost `:free` model variants. For a coding-agent workload,
[Poolside](https://poolside.ai)'s Laguna S 2.1 is a solid free pick — it's one of the
most-used free models on OpenRouter and is purpose-built for coding-agent tasks
(70.2% on Terminal-Bench 2.1), with a 262K context window and tool-calling support:

```bash
AGENTLAB_MODEL=poolside/laguna-s-2.1:free
```

Free `:free` variants are rate-limited and rotate on OpenRouter's side, so treat this as
an experimentation/fallback option rather than a production default.
