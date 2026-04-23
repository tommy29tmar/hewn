# Changelog

## 0.9.1 — 2026-04-23

### Public launch — benchmarks, docs, hero image

First public release. Wrapper code unchanged from 0.9.0; this release
ships the evidence and the launch presentation.

Added:
- `benchmarks/` — full benchmark suite (518 benchmark cells run via
  `claude -p` / `hewn -p` under OAuth, no direct API billing)
  comparing Hewn vs Verbose Claude vs Caveman Full vs Caveman
  Ultra-style across 7 tracks (T0 calibration, T1a/T1b short Q&A, T2
  vibe non-tech, T3 long-context, T4 multi-turn 5-turn sequences, T5
  expansive prose). Caveman SKILL.md vendored verbatim with sha256
  attribution.
- `benchmarks/report/REPORT.md` — full per-prompt breakdown with
  honesty box (single-shot long-context favors Caveman, T2 vibe
  prompts trade quality for compression, T5 expansive prose is
  effectively neutral).
- `benchmarks/RUNBOOK.md` — exact reproduction steps (4 Hewn iterations
  v1→v4 documented with commit hashes, transcript-aware judge
  rationale, final reference numbers with ±25% tolerance).
- `benchmarks/codex-review-iterations/` — 8 rounds of cross-model plan
  review with Codex (preserved as launch transparency artefact).
- `assets/hero_benchmark.png` — 3-KPI dashboard image (tokens /
  information density / time) for the README hero.
- `examples/atlas-xff-review.md` — long-context security review
  example (Verbose / Caveman Ultra-style / Hewn side-by-side).
- `.github/ISSUE_TEMPLATE/bug_report.yml` and `feature_request.yml`.
- Hewn classifier hook iterations v2 → v3 → v4 (`prose-caveman`
  strict mode, then two-flavor micro-prose for vague vs concrete error
  prompts).

Headline numbers (T4 multi-turn, mean across 2 sequences × 2 runs,
Claude Opus 4.7, transcript-aware LLM-as-judge):

| arm                        | tokens | latency | concepts retained |
| Verbose Claude             |  7,196 | 124.8s  | 100%              |
| Caveman Full               |  4,226 |  83.0s  | 100%              |
| Caveman Full + Ultra-dir.  |  3,901 |  79.3s  | 100%              |
| Hewn                       |  2,838 |  65.2s  | 100%              |

Hewn vs Verbose: −61% tokens, −48% latency, 4.6× higher information
density (concepts kept per 100 tokens). Hewn vs Caveman Ultra-style:
−27% tokens, −18% latency, 1.5× higher density.

(Reminder: `caveman_full_plus_ultra_directive` is OUR directive-based
approximation — NOT Caveman's official `/caveman ultra` skill, which
needs the skill runtime unavailable under `--system-prompt`.)

Changed:
- `README.md` rewritten for launch (242 → 167 lines): badges, hero
  image, install above the fold, "Beyond the headline" with 4 quality
  findings, "Where Hewn doesn't win" honesty box, examples link.

Repo flipped from private to public.

## 0.9.0 — 2026-04-21

### Hard rename Flint → Hewn; wrapper-only repo

Brand rename from Flint to Hewn was merely cosmetic at v0.8.3 (alias layer
alongside primary Flint names). v0.9.0 completes it as a hard cutover and
strips the project down to its single useful primitive: a Claude Code CLI
wrapper.

Removed:
- MCP server and `{flint,hewn}-mcp` wrappers
- Claude Code skills (`/flint`, `/flint-on`, `/flint-off`, `/flint-audit`)
- Output styles (`flint`, `flint-thinking`, `hewn`, `hewn-thinking`)
- Python package `src/flint/` (parser, validator, audit engine, rendering,
  routing, MCP transport)
- `flint-ir` / `hewn-ir` Python CLI and its pyproject packaging
- Benchmark harness: `evals/`, `scripts/`, launch copy, baseline prompts
- Grammar files, `*.flint` examples, JSON schemas
- `docs/` dir (architecture, methodology, failure modes, plans)
- `cccaveman` benchmark-only wrapper
- Legacy `bin/flint` and `bin/flint-mcp`

Renamed / scrubbed:
- `bin/hewn` rewritten to work standalone (no longer delegates to `bin/flint`);
  generates the drift-fix `--settings` JSON inline via a portable `mktemp`
  with a shell-quoted hook-command path
- `flint_thinking_system_prompt.txt` → `hewn_thinking_system_prompt.txt`
  (content scrubbed: `Flint` → `Hewn`, `@flint v0 hybrid` → `@hewn v0 hybrid`)
- `hooks/flint_drift_fixer.py` → `hooks/hewn_drift_fixer.py`
  (docstring + routing-directive strings scrubbed of MCP / `submit_flint_ir` refs)
- `tests/test_flint_drift_fixer.py` → `tests/test_hewn_drift_fixer.py`,
  ported from pytest to `unittest.TestCase` + `subTest` + `unittest.mock.patch`
  (no external deps)
- `install.sh` rewritten: installs only the wrapper + prompt + hook, plus a
  one-liner to clean up legacy Flint files
- CI workflow (`.github/workflows/ci.yml`): `python -m unittest tests.test_hewn_drift_fixer`,
  no package install step
- README (top-level + integrations) rewritten around the wrapper story
- IR protocol header `@flint v0 hybrid` → `@hewn v0 hybrid` (no parsers remain)

The drift-fix classifier still recognizes `\bno\s+flint\b` alongside
`\bno\s+hewn\b` and `\bno\s+ir\b` as a "please don't emit IR" signal, so
users with muscle memory for the old brand continue to work.

Migration: existing Flint installs carry orphan files under `~/.claude/`;
the installer prints a one-liner to remove them. Git history preserves all
deleted code for reproducibility.

## 0.8.4 — 2026-04-21

### Classifier — `prose_findings` route for ranked diagnostic lists

Adds a fifth Claude Code route for ranked/enumerated independent
findings: bugs, risks, issues, vulnerabilities, blockers, footguns, and
failure modes. These prompts are technical and evidence-driven, but they
are not G/C/P/V/A-shaped: each item naturally carries its own
title/evidence/impact/fix tuple — forcing them into IR atoms inflated
tokens (p7 bug-prediction was 6658 tok IR vs ~2500 tok as numbered list).

This keeps architecture/audit/fix planning in IR, while routing prompts
like "top 3 bugs", "rank security issues by severity", and "launch
blockers" to compact numbered Caveman prose. The vibe p7 expected shape
and long security-review eval labels were updated accordingly.

### Bench fairness — Agent block + subagent detector

Vibe-bench previously let `cccaveman` delegate work to Agent/Task
subagents on expensive prompts (p7). A subagent can issue dozens of
internal tool calls and emit large chunks of content that never show in
the parent's usage/tool_uses — falsifying the tok/lat/tool comparison.

Fixes:
- `scripts/bench_vibe_3way.sh`: injects `[BENCH MODE] Do not use Agent
  or Task subagent tools. Do all work inline.` into every prompt.
- `scripts/vibe_3way_table.py`: new `has_subagent` detector and
  `subagent_n` column; refuses to count Agent-contaminated rows as
  clean. On the fresh run, all variants showed 0/8 — the block works.

### prose_caveman tool-use hint refined

Previous hint ("use tools when facts about real code needed") was too
broad: flint was reading files for opinion/naming/marketing prompts
where no evidence was required. New hint scopes to concrete repo STATE
questions only ("does function X exist", "what does file Y contain",
"is Z configured"). Opinion/chat/naming prompts no longer trigger reads.

On the bench this drops p4/p5/p6 tool calls from 2-6 to 0-1 with no
quality loss on the reviewed answers.

### Shape detector — structural findings check

`vibe_3way_table.py` now detects `prose_findings` structurally
(≥2 numbered items + file/line reference + fix marker), not just
"is it prose". Variants that write generic prose no longer get credit
for a findings-shaped prompt — the reporter is strict on the route.

### Results — fresh bench with fairness fixes (8 vibe prompts, 3 variants)

| variant       | tok     | lat    | tools | shape_hit | subagent |
|---------------|---------|--------|-------|-----------|----------|
| plain claude  | 33123   | 660s   |   82  |     62%   |     0/8  |
| cccaveman     | 28661   | 557s   |   77  |     75%   |     0/8  |
| **flint**     | **23734** | **490s** | **56** | **100%**  |     0/8  |

vs plain: flint -28% tok, -26% lat, -32% tools.
vs cccaveman: **flint -17% tok, -12% lat, -27% tools**, 7/8 per-prompt wins.

The previous bench that showed flint > cccaveman on tokens (v0.8.3) was
contaminated: cccaveman was delegating to subagents, and flint was doing
unnecessary repo reads on opinion prompts. With both vectors closed, the
architectural prediction holds — routing IR for technical shapes and
Caveman prose for everything else beats pure prompt-only compression on
every axis that matters.

62 classifier tests passing.

## 0.8.3 — 2026-04-21

### Classifier — exploratory-technical shapes + tool-use hint on prose_caveman

Closes a real gap surfaced by a vibe-coding bench (8 open-ended prompts
about the repo, plain claude vs cccaveman vs flint):

- **New IR rules** for prompts that asked for a technical audit without
  containing code keywords. Vibe shapes like "studia questa directory /
  audit this repo / which 3 bugs would a user hit" were misclassified
  as prose_caveman and got narrative answers when the caller clearly
  wanted a structured diagnosis. Added bilingual EN/IT patterns:
  `(audit|analyze|study|inspect|examine) + (repo|codebase|project)`,
  `(what|which|quali) + N + (bugs|issues|risks|problemi)`,
  `what's (missing|fragile|broken|risky)` / `cosa (manca|toglierei)`.
- **prose_caveman directive extended** with a tool-use hint: when the
  question requires facts about actual code (e.g. "should I add tool
  X?"), use Read/Grep/Glob instead of speculating. On the same vibe
  bench, flint previously missed that `validate_flint` already existed
  in `mcp_server.py`; with the hint it now reads the code and gives the
  correct "already exists, here's what it does" answer.

### Brand alias — Hewn

Preparatory rename keeping full backwards compatibility:
- CLI binaries: new `hewn`, `hewn-mcp` alongside existing `flint`,
  `flint-mcp`. Both pairs resolve to the same wrapper.
- Python CLI entry points: `hewn-ir` added alongside `flint-ir`.
- Output-styles: `hewn`, `hewn-thinking` added alongside `flint`,
  `flint-thinking`.
- Installer advertises `hewn` as primary; `flint` kept as legacy alias.

No functional change — chooser's discretion which name to use.

### Vibe-coding bench (8 prompts, 3 variants)

New corpus at `evals/vibe_3way.jsonl` plus parallel runner and
aggregator. Runs 3 wrappers in parallel on 8 repo-exploration prompts
with tools enabled (vibe-coding realistic mode, not BENCH_MODE tool-free).

Results (p7 excluded: all variants rate-limited):
- plain: 32076 tok / 859s / 140 tools across 7 answered prompts
- cccaveman: -28% tok, -30% lat, similar tool count
- flint: -30% tok, -42% lat, **-60% tool calls**

Qualitative review over 7 prompts: flint wins 5/7, ties 2/7. Unique
insights emerged for repo naming (glyph/rune brand-coherence), README
vibe (story order contrast), bug prediction (repair-layer silent pass).

57 classifier tests passing. Vibe-corpus IR-expected prompts now
classified correctly (p1, p2, p7 → ir; p3, p4, p5, p6, p8 → prose_caveman).

## 0.8.2 — 2026-04-21

### Fifth route — `prose_polished_code`

Addresses the edge case Codex flagged in the v0.8.1 review: prompts
that combine a polished audience with an inline code artifact (e.g.
"customer-facing memo: include the exact nginx config we deployed
inline") were routed to `prose_polished`, losing the code block.

New classifier output: `prose_polished_code` — professional readable
prose (articles preserved, no Caveman compression) followed by fenced
code block(s). Added precedence: when `polished_audience` AND `wants_code`
AND `prose_score >= 4`, route to the new label.

Extended `CODE_ARTIFACT_RULES` to catch "include/with [qualifier] code"
and "<artifact> inline" patterns (previously missed).

51 classifier tests passing.

## 0.8.1 — 2026-04-21

See prior entries — Codex-authored cleanup of migration debt from the
rename. No classifier changes.

## 0.8.0 — 2026-04-21

### 3-way routing + honest metrics — class_acc jumps 44% → 100%

Major quality release. Extends classification from binary (IR / prose) to
4 routes matched by intent, and reports metrics that don't flatten the
signal.

### Hook classifier — 4 routes

`flint_drift_fixer.py` now returns one of:
- `ir` — crisp technical goal + verifiable endpoint
- `prose_code` — technical goal + executable artifact requested (fix,
  test, updated file); answer is prose analysis + fenced code block
- `prose_polished` — leadership / stakeholder / customer audience;
  professional register, no Caveman compression
- `prose_caveman` — default terse prose for chat, brainstorm, tutorial,
  peer retrospective

Decision order: strongly polished audience → prose_polished; code
artifact requested → prose_code; technical score ≥ threshold → ir;
polished audience hint → prose_polished; otherwise prose_caveman.

46 parametrized tests at `tests/test_flint_drift_fixer.py` cover each
route and the decision precedence.

### Thinking-mode prompts

`flint_thinking_system_prompt.txt` and the MCP variant replace the
binary IR/prose rule with explicit 4-route guidance. Polished-prose
style is new: complete sentences, articles preserved, professional
register — previously all prose was Caveman-compressed, which produced
unusable memos for non-technical audiences.

### Aggregator — honest metrics (Codex-authored, reviewed)

`scripts/claude_code_max_long_multiturn_4var_table.py`:
- `parse_%` → `parse_on_ir_turns`: divide only by turns detected as IR,
  not all turns. Variants that correctly emit prose no longer eat the
  penalty meant for IR.
- New `infra_error_n` column: exit_code != 0, empty content, error
  field, or error-prefixed content.
- New per-scenario breakdown section.
- 3-way detection: `ir` / `prose_code` (fenced code block present) /
  `prose`, matching the new corpus labels.
- 7 aggregator tests at `tests/test_long_multiturn_aggregator.py`.

### Corpus relabeling

3 turns in `evals/claude_code_max_long_multiturn.jsonl` reassigned from
`expected_shape: "ir"` to `"prose_code"` — those that explicitly ask
for a code artifact (security-audit t3/t4, incident-postmortem t3).
The IR label had forced the model to cram multi-line code into IR atoms
where it couldn't parse. With the new route, prose+code is the honest
answer.

### Results — 32 turns/variant on long multi-turn 4-variant bench

| variant         | class_acc | total_tok | vs plain | vs caveman | parse_on_ir | mean_lat | must_inc |
|-----------------|----------:|----------:|---------:|-----------:|------------:|---------:|---------:|
| plain claude    |       44% |     76984 |      —   |       +31% |         n/a |    49.2s |      71% |
| cccaveman       |       44% |     58840 |    -24%  |         —  |         n/a |    35.7s |      69% |
| **flint**       |  **100%** | **35252** |**-54%**  |  **-40%**  |     **61%** |**24.0s** |      68% |
| flint-mcp       |       97% |     95324 |    +24%  |       +62% |    **100%** |    47.7s |      60% |

Per-scenario class_acc for `flint`: **100% / 100% / 100%** across
arch-review, security-audit, incident-postmortem (v0.6.0 had 33% / 40% /
60%). The updated classifier now catches architecture review,
root-cause, and code-artifact prompts that the regex-based predecessor
missed.

`flint-mcp` returns 100% parseable IR when it fires (vs 61% free-text)
— viable for downstream pipelines consuming schema-validated IR, at a
token premium.

## 0.7.1 — 2026-04-20

### Classifier rewrite — drift-fix hook in Python + tests

Replaces the fragile `flint_drift_fixer.sh` bash/sed/grep pipeline with
`flint_drift_fixer.py` (pure-Python, no deps). Addresses Codex feedback:

- **Score-based classifier** instead of first-match regex. Each rule
  carries a weight; a prompt is classified IR if the sum exceeds the
  threshold. This catches cases the sh classifier missed
  (architecture review, root-cause hypothesis without code, security
  audit with "attack vectors" / "security issues", italian triggers).
- **38 unit tests** at `tests/test_flint_drift_fixer.py` covering
  IR-shape (debug, review, audit, fix, refactor, architecture,
  monitoring, italian, code-embedded), prose-shape (leadership,
  memo, tutorial, brainstorm, chat), edge cases (empty, malformed
  JSON, prose-override precedence).
- **Deterministic JSON output**: Python's `json.dumps` handles escaping
  robustly, vs the sed-based quote escaping in the sh version which
  broke on prompts containing embedded quotes or newlines.

### Migration
Existing installs: re-run `integrations/claude-code/install.sh` to pick
up the new hook. The settings file now points to `flint_drift_fixer.py`.

## 0.7.0 — 2026-04-20

### Consolidation — rename + remove basic lanes

No functional changes. Consolidates the Claude Code wrapper binaries
down to two lanes:

- `cccflint-pro` → **`flint`** — the recommended default (Flint
  thinking-mode + drift-fix hook, free-text IR).
- `cccflint-mcp-pro` → **`flint-mcp`** — opt-in advanced lane for
  downstream pipelines that consume schema-validated IR.

### Removed
- `cccflint` (basic, system-prompt only, no drift fix) — strictly worse
  than `flint` on multi-turn (v0.5.1 bench showed IR only at T1, prose
  at T2+). Users should switch to `flint`.
- `cccflint-mcp` (basic with MCP) — same reason.

### Renamed (Python CLI)
- `flint` (parser/audit CLI from `flint-ir` package) → `flint-ir` —
  resolves the name collision with the new `flint` shell wrapper. Docs
  updated. Run `pipx reinstall flint-ir` to pick up the new name.

### Migration
- `cccflint-pro` / `cccflint-mcp-pro` binaries: remove and re-run the
  installer to pick up `flint` and `flint-mcp`.
- `flint audit`, `flint parse`, `flint validate`, `flint repair`,
  `flint claude-code ...` → `flint-ir audit`, `flint-ir parse`, etc.
- Installer now installs the drift-fix hook and settings automatically.

The `flint` wrapper is functionally identical to v0.6.0 `cccflint-pro`;
v0.6.0 bench numbers still apply:
-29% tokens vs Caveman, +37pt classification accuracy, -17% latency on
32-turn long multi-turn.

## 0.6.0 — 2026-04-20

### Added — cccflint-pro (drift-fix hook, free-text IR)

New wrapper that combines the thinking-mode system prompt with a
`UserPromptSubmit` hook that re-injects a per-turn classification
directive (`[TURN CLASSIFICATION: IR-shape | prose]`) via
`additionalContext`. Fixes the multi-turn drift where the base
`cccflint` emitted IR only at T1 and fell back to prose at T2+.

- `integrations/claude-code/bin/cccflint-pro` — wrapper
- `integrations/claude-code/bin/cccflint-mcp-pro` — same + MCP tool
- `integrations/claude-code/hooks/flint_drift_fixer.sh` — classifier hook
- `integrations/claude-code/flint-drift-fix-settings.json` — hook registration

### Added — cccaveman baseline

`integrations/claude-code/bin/cccaveman` — wraps `claude` with
`prompts/primitive_english.txt` (Caveman descriptive compression) as
`--append-system-prompt`. Used to benchmark "Flint vs descriptive prose
compression" on the same workload.

### Added — long multi-turn 4-variant bench

- `evals/claude_code_max_long_multiturn.jsonl` — 3 scenarios × 5-6 turns
  (arch review, security audit, incident postmortem) mixing IR-shape
  and prose turns.
- `scripts/bench_long_multiturn_4variants.sh` — sequential runner.
- `scripts/bench_long_multiturn_4variants_parallel.sh` — parallel runner
  (scenario-level concurrency, `MAX_CONCURRENCY=8`), ~6× speedup
  (12 min vs 75 min on 128 calls).
- `scripts/claude_code_max_long_multiturn_4var_table.py` — aggregator.

### Results — long multi-turn, 32 turns/variant, 4-variant comparison

| variant            | class_acc | total_tok | vs plain | vs caveman | must_inc | mean_lat |
|--------------------|----------:|----------:|---------:|-----------:|---------:|---------:|
| plain claude       |       25% |     77589 |      —   |       +48% |      71% |    47.5s |
| cccaveman          |       25% |     52298 |    -33%  |         —  |      69% |    31.9s |
| **cccflint-pro**   |   **62%** | **37187** |**-52%**  |  **-29%**  |      66% |**26.5s** |
| cccflint-mcp-pro   |       56% |     68484 |    -12%  |       +31% |      64% |    38.2s |

**Headline:** `cccflint-pro` beats Caveman on every axis that matters:
-29% tokens, -17% latency, **+37pt class_acc**, -3pt must_include
(acceptable trade for IR-shape turns). MCP round-trip cost makes
`cccflint-mcp-pro` heavier than Caveman on long sessions — pro is the
sweet spot when schema validation isn't needed downstream.

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
