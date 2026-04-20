# Changelog

## 0.5.1 — 2026-04-20

### Fixed — multi-turn bench metric correction

The v0.5.0 multi-turn 4-cell table reported cccflint essentially tied
with plain claude (14692 vs 14316 tokens, +2.6%) on 2 scenarios × 4
turns. That number was wrong. Root cause: in RUNS=1, the bench's claude
subprocesses inherited user-settings permissions (auto-approve Bash /
Read / Write / Edit / Task / MCP tools) and the scenario prompts
contained agentic verbs ("write the repro test", "propose fix code").
The model under cccflint's "CRISP TECHNICAL GOAL + VERIFIABLE ENDPOINT"
instruction went into agent mode — on deep-debug T2, cccflint emitted
17 tool calls (11 × Bash, Read, Write, 3 × Edit, Grep), inflating
`output_tokens` with tool_use args + tool_result content. Plain claude
in the same scenario only used 2 tools.

The metric was measuring "how hard did the variant work to verify the
answer" not "how compact is the final response". Agent mode on
cccflint: 7323 tok on one turn alone.

### Fix

- Scenario prompts neutralized: changed agentic verbs ("write", "ship",
  "apply", "run") to descriptive verbs ("describe", "show inline",
  "as a snippet in your response").
- Bench script injects a `[BENCH MODE] Do not use any tools` directive
  at the end of every user prompt (cccflint+MCP cell allows
  `submit_flint_ir` only).
- Aggregator tracks `agent_n` (turns with non-flint tool calls) and
  `clean_tok` (tokens from agent-free turns only). Contaminated turns
  are flagged. On the fixed bench, all 4 cells showed `agent_n = 0/24`.

### Corrected numbers (RUNS=3, 24 samples per cell, agent-free)

| variant          | class_acc | ir_hit | tool_hit | parse_% | total_tok | mean_lat |
|------------------|----------:|-------:|---------:|--------:|----------:|---------:|
| plain claude     |       25% |     0% |       0% |      0% |     34248 |    29.4s |
| **cccflint**     |   **54%** |**29%** |       0% |     21% | **27404** | **24.3s** |
| plain + MCP      |       25% |     0% |       0% |      0% |     43384 |    34.7s |
| cccflint + MCP   |       46% |    21% |  **21%** |     21% |     41304 |    31.6s |

**Headlines:**
- `cccflint` vs plain: **-20% token, -17% latency** on multi-turn
  (consistent with v0.4.0 -24% short, v0.4.1 -53% long benches).
- Per-scenario: deep-debug -12.6%, mixed-security **-32.7%**.
- Classification accuracy: 54% vs 25% (2.2× plain claude).
- **MCP cells are heavier**: `plain + MCP` is the worst (43384 tok) —
  the tool is available but never called without a system-prompt push,
  so it only adds the MCP tool-catalog tax to input.
- `cccflint + MCP` sits at 41304 tok (+51% vs cccflint) — tool
  round-trip overhead. Use only when parser-validated IR is required
  by downstream tooling.

### Guidance (revised)

- **Default**: `cccflint`. -20% tokens, -17% latency, 100% non-invasive.
- **Strict-parse downstream pipeline**: `cccflint-mcp`. Trade +51%
  tokens for API-schema-validated IR.
- **Never**: `plain + MCP` (worst outcome — MCP catalog tax without
  benefit).

## 0.5.0 — 2026-04-20

### Added — MCP server + `cccflint-mcp` wrapper

- `src/flint/mcp_server.py` — a Model Context Protocol server exposing three
  tools over stdio: `submit_flint_ir` (schema-enforced IR emission),
  `validate_flint` (parse a raw Flint document), and `audit_explain`
  (render prose from an IR). The `submit_flint_ir` input schema encodes
  Flint atom grammar as a regex pattern, so any malformed atom is rejected
  at the API layer before reaching the tool.
- `integrations/claude-code/bin/cccflint-mcp` — second wrapper that
  launches `claude --append-system-prompt <thinking-mcp-prompt> --mcp-config
  <flint-mcp>`. The thinking-mcp system prompt instructs the model to call
  `submit_flint_ir` for IR-shape tasks and pass the tool's rendered output
  to the user verbatim.
- `integrations/claude-code/flint_thinking_mcp_system_prompt.txt` — MCP
  variant of the thinking-mode prompt.
- `integrations/claude-code/mcp-config.json` — template config that
  launches the Flint MCP server via `python3 -m flint.mcp_server`.

### Multi-turn 4-cell bench

- `evals/claude_code_max_multiturn.jsonl` — 2 scenarios × 4 turns each
  (deep-debug-auth with 400-line Python module, mixed-security-review with
  multi-stage IR↔prose flow).
- `scripts/bench_claude_code_max_multiturn.sh` + `...table.py` — 2-cell
  (plain vs cccflint) bench over multi-turn with session resumption
  (`claude -p --resume`).
- `scripts/bench_claude_code_max_4cell.sh` + `...4cell_table.py` — 4-cell
  (plain, cccflint, plain+MCP, cccflint+MCP) bench with the same scenarios.

### Measured (multi-turn, 2 scenarios × 4 turns, Claude Max, RUNS=1)

| variant           | class_acc | ir_hit | tool_hit | total_tok | mean_lat |
|-------------------|----------:|-------:|---------:|----------:|---------:|
| plain claude      |       25% |     0% |       0% |     14316 |    35.9s |
| cccflint          |   **50%** |    25% |       0% |     14692 |    37.5s |
| plain + MCP       |       25% |     0% |       0% |     16390 |    44.4s |
| cccflint + MCP    |   **50%** |    12% |  **25%** |     17867 |    44.9s |

Findings:
- **Multi-turn drift**: IR emission happens at turn 1 of a fresh session,
  drifts to prose on turns 2-4 for all variants. The system prompt loses
  against accumulated conversation context. This is Claude Code session
  dynamics, not a Flint-specific issue.
- **MCP tool needs system-prompt push**: plain+MCP (tool available but no
  instruction) = same behavior as plain claude. Tool must be recommended
  by the system prompt.
- **MCP adds +20% token overhead** due to tool round-trip
  (tool_use + tool_result + re-emission by the model). Trade-off: the
  IR emitted via the tool is API-validated (100% parseable by construction).
- **cccflint's prose (turns 2-4) still beats plain claude prose** on
  mixed-security scenario (2856 vs 5694 cumulative, -50%) because the
  Caveman discipline applies even when IR doesn't trigger.

### Product recommendation

- **Default**: `cccflint` (v0.4.1 path) — zero overhead, best token savings
  on turn 1, Caveman prose on follow-ups.
- **Power user with downstream tooling**: `cccflint-mcp` (v0.5 new path)
  — schema-enforced IR at +20% token cost, 100% parseable when the tool
  fires.
- **Never use**: `plain + MCP` alone. The tool is unused without prompt
  push, so it only adds cost.

## 0.4.1 — 2026-04-20

### Added — long-prompt benchmark

- `evals/claude_code_max_long_prompts.jsonl` — 5 realistic working-session
  prompts (300–700 input tokens each): 400-line Python auth module debug,
  large security-diff review, multi-file callback→async refactor,
  full-system architecture walkthrough, open-ended tradeoff discussion.
- `scripts/bench_claude_code_max_long.sh` + `claude_code_max_long_table.py`
  — parallel bench infra for the long corpus.

### Measured — compression scales with context length

| corpus                  | plain mean | cccflint mean | savings |
|-------------------------|-----------:|--------------:|--------:|
| short (≤100 tok input)  |    537 tok |       409 tok |    -24% |
| **long (300-700 tok)**  | **2799 tok** |  **1313 tok** | **-53%** |

- **Classification: 100%** (5/5 tasks correctly routed IR vs prose,
  plain claude at 40%).
- **Parser-pass on IR-shape outputs: 100% (9/9)** — grammar compliance
  holds under long context.
- **Latency: -36%** (47s → 30s mean).
- Individual IR task peak: `long-debug-auth-module` from 1886 tok
  (plain markdown) to 402 tok (Flint IR) — **-79% on the same task**.

Pattern confirmed: the longer the prompt, the bigger the cccflint win.

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
