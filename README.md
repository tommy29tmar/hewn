# Hewn

<!-- Static badges while the repo is private. When flipping public, swap to:
     [![CI](https://img.shields.io/github/actions/workflow/status/tommy29tmar/hewn/ci.yml?branch=main&label=CI&style=flat-square)](https://github.com/tommy29tmar/hewn/actions/workflows/ci.yml)
     [![License: MIT](https://img.shields.io/github/license/tommy29tmar/hewn?style=flat-square)](LICENSE) -->
[![License: MIT](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
[![Status: public preview](https://img.shields.io/badge/status-public%20preview-84cc16?style=flat-square)](#)
[![Made for Claude Code](https://img.shields.io/badge/made%20for-Claude%20Code-84cc16?style=flat-square)](https://claude.com/claude-code)

> **Make Claude Code talk less. Same answers, ~3× fewer tokens.**
>
> *why burn many token when few do job*

Claude talks too much. Hewn makes it get to the point — without losing
what the prompt actually asked for.

No proxy. No telemetry. Default `claude` untouched.

![Multi-turn coding session — Hewn vs Caveman vs Verbose Claude](assets/hero-benchmark.png)

> Multi-turn coding session, Claude Opus 4.7, same model and prompts
> across all four arms. Concept retention measured by transcript-aware
> LLM-as-judge.
>
> Full methodology, raw snapshots, and per-track evidence:
> [`benchmarks/report/REPORT.md`](benchmarks/report/REPORT.md) ·
> [`benchmarks/RUNBOOK.md`](benchmarks/RUNBOOK.md) for reproduction.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/tommy29tmar/hewn/main/integrations/claude-code/install.sh | bash
```

## Use

```bash
hewn                     # interactive session with Hewn thinking-mode
hewn -p "your prompt"    # non-interactive
```

Any flag accepted by `claude` is forwarded:
`hewn --model claude-opus-4-7 -p "…"`.

The default `claude` command is untouched. Want normal Claude? Just
type `claude`.

## Beyond the headline

- **Long-context task comprehension** — On a long-context security
  review with compact IR-style task framing, Hewn is the **only arm
  that completes the task** (89% concepts captured) — Verbose Claude,
  Caveman Full, and Caveman Ultra-style all reply *"no task specified"*
  (0%). See [`examples/atlas-xff-review.md`](examples/atlas-xff-review.md)
  for the full input/output triplet.
  *Source: T3 `rate-limit-xff-review`, 3 runs per arm.*

- **The drift-fix hook is doing real work** — In multi-turn sessions,
  removing Hewn's classifier hook costs **+4,700 to +5,300 cumulative
  tokens** per 5-turn workflow. The hook earns its keep.
  *Source: T4, `hewn_full` vs `hewn_prompt_only`.*

- **Causal savings vs default Claude** — On Caveman's own short-Q&A
  prompts, Hewn cuts output by a median of **52%** (range 17–92%, best
  case `fix-node-memory-leak` at 92%) compared to unprompted Claude on
  the same model.
  *Source: T1b, 10 prompts × 3 runs per arm.*

- **No ultra-tax on technical literals** — Caveman Ultra-style's
  aggressive compression drops required exact strings
  (`"X-Forwarded-For"`, `"401"`) to 80% preservation; Hewn keeps them
  at **100%**.
  *Source: T1b literal preservation, 15 judgments per arm.*

→ Full per-prompt breakdown and raw judgments:
[`benchmarks/report/REPORT.md`](benchmarks/report/REPORT.md)

## Where Hewn doesn't win

Honesty matters. The benchmark shows three areas where Hewn is not the
right tool:

- **Expansive prose tasks** (apology emails, release notes) — all arms
  including Hewn produce near-stub responses on these prompts (~0%
  rubric concepts across the board). Use plain `claude` for marketing
  copy.
- **Vibe / non-tech prompts** — Hewn 63% concept coverage vs Caveman 78%.
  Hewn is agent-mode (asks before guessing); Caveman is tutorial-mode
  (enumerates options). Different design philosophy, both valid.
- **Tasks that genuinely need a long answer** — when the prompt
  legitimately requires a full plan, Hewn uses similar tokens to
  baseline. Compression gracefully degrades when there's nothing to cut.

## How it works

Hewn wraps `claude` with two pieces:

1. **A thinking-mode system prompt** appended via `--append-system-prompt`,
   which routes each turn to one of six answer shapes (IR, prose+code,
   prose-findings, prose-polished, prose-polished+code, prose-caveman)
   based on task structure.
2. **A per-turn drift-fix hook** registered via `--settings`, which
   classifies every user prompt and re-injects the routing directive as
   `additionalContext`. This prevents the multi-turn drift you see when
   relying on the system prompt alone.

Technical tasks may route into a tiny IR:

```text
@hewn v0 hybrid
G: goal
C: constraints
P: plan
V: verify
A: action
```

Most users do not need to care. Run `hewn`; Claude gets shorter.

## Locales

Hewn ships classifier patterns for `en`, `it`, `es`, `fr`, `de`. The
locale is auto-detected from `$LANG` at run time, so non-English shells
just work out of the box. Example: `LANG=it_IT.UTF-8` loads `en + it`
automatically.

Override when needed:

```bash
hewn --locale en,it        # force this stack for one invocation
export HEWN_LOCALE=en,es   # persistent in your shell rc
export HEWN_LOCALE=en      # force English-only
```

Precedence: `--locale` > `HEWN_LOCALE` > `$LANG` auto-detect > English-only.
Details: [integrations/claude-code/README.md](integrations/claude-code/README.md#locales).

## Examples

- [Long-context security review (Atlas API)](examples/atlas-xff-review.md) —
  side-by-side Verbose / Caveman Ultra-style / Hewn output on a real
  16k-token handbook + IR-style task.

## What gets installed

- `~/.local/bin/hewn`
- `~/.claude/hewn_thinking_system_prompt.txt`
- `~/.claude/hooks/hewn_drift_fixer.py`
- `~/.claude/hooks/locales/{en,it,es,fr,de}.py`

That is it.

## Uninstall

```bash
rm -f ~/.local/bin/hewn \
      ~/.claude/hewn_thinking_system_prompt.txt \
      ~/.claude/hooks/hewn_drift_fixer.py
rm -rf ~/.claude/hooks/locales
```

## Contributing

PRs welcome — especially expanding locale classifier patterns
(`integrations/claude-code/hooks/locales/<code>.py`) with real-prompt
evidence in non-English languages. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
