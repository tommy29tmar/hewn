# Changelog

## 0.4.0 — 2026-04-20

### Added — Claude Code Max always-on path

- **`cccflint` wrapper** (`integrations/claude-code/bin/cccflint`). Runs
  `claude --append-system-prompt "$FLINT_THINKING_PROMPT"` so the Flint
  instructions reach system-prompt level inside Claude Code. Non-invasive:
  a separate binary, never shadows the default `claude` command. Installed
  to `~/.local/bin/cccflint` by `install.sh`.
- **`flint-thinking` output-style** (`integrations/claude-code/output-styles/flint-thinking.md`).
  Dual-mode system prompt: Caveman-shape prose by default (all human
  deliverables: RFCs, tutorials, explanations, brainstorms), Flint IR when
  the task shape is IR (debug, code review, refactor, architecture with
  crisp goal + verifiable endpoint). Installed as a Claude Code output-style
  alongside `flint`.
- **`flint_thinking_system_prompt.txt`**. The 32-line prompt payload used by
  both `cccflint` and the `flint-thinking` output-style.
- **Claude Code Max benchmark** (`scripts/bench_claude_code_max.sh` +
  `scripts/claude_code_max_table.py`, corpus
  `evals/claude_code_max_prompts.jsonl`). Measures plain `claude -p` vs
  `cccflint -p` on a 6-prompt mix (3 IR-shape + 3 prose-shape). Uses the
  user's Claude Max plan; zero Anthropic API cost.

### Measured (Claude Opus 4.7, Claude Max plan, 3 runs × 6 prompts)

| variant          | classification | class_ir | class_prose | mean out tokens | parser-pass (IR outputs) |
|------------------|---------------:|---------:|------------:|----------------:|-------------------------:|
| plain `claude`   |            50% |       0% |        100% |             537 |                       0% |
| `cccflint`       |       **100%** | **100%** |    **100%** |         **409** |                  **89%** |

`cccflint` delivers 100% task-shape classification (IR for technical,
prose for human), cuts mean output tokens 24% versus plain `claude` on the
mixed corpus, and produces IR that the `flint` parser validates 89% of the
time on IR-shape outputs (8 of 9 samples across 3 runs × 3 IR-shape tasks).
This exceeds the ~80% parser-pass rate of strict Flint on its own 10-task
stress corpus.

### Discovery documented

- Claude Code output-styles, hooks, skills, and CLAUDE.md all load as
  **context**, not system prompt. Their instructions lose conflicts with
  Claude Code's built-in system prompt. The only Claude Code mechanism
  that reaches system level is the `--append-system-prompt` CLI flag,
  which `cccflint` wraps. `docs/architecture.md` and `docs/failure_modes.md`
  now document this deployment reality.

### Changed

- `install.sh` distributes three new artifacts (`cccflint`, thinking-mode
  prompt, `flint-thinking` output-style) in addition to the existing
  strict skills and output-style.
- README hero section adds a direct pointer to the Claude Code Max path.
- Architecture doc frames the shipped artifacts as two complementary
  payloads (strict for API, thinking for Claude Code).

### Not changed

- Strict Flint system prompt (`flint_system_prompt.txt`) unchanged.
  API users calling Claude directly with this as `system` continue to
  get the benchmark-proven 4× tokens / 3× latency / +9pt coverage on
  the 10-task stress corpus.
- Default Claude Code `claude` command untouched. No PATH shim, no
  `~/.claude/settings.json` modifications.

## 0.3.0 — 2026-04-18

- Add `/flint-on`, `/flint-off`, `/flint-audit` slash commands.
- Add `flint-thinking` Monday plan.

## 0.2.2 — earlier April 2026

- Fix: `/output-style` is not a slash command (launch blocker).

## 0.2.1 — earlier April 2026

- Prep launch: hero image, deep docs, launch copy.

## 0.2.0 — earlier April 2026

- Rename SIGIL → Flint. Consolidate stress bench.
