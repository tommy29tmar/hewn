# Hewn benchmarks

Reproducible benchmark of Hewn vs Verbose Claude vs Caveman, run via
`claude -p` CLI under an OAuth subscription (no direct API key billing).

## What this measures and what it doesn't

| Metric | Source | Status |
|---|---|---|
| Output tokens (tiktoken o200k_base) | `tiktoken` over response text | matches Caveman `evals/measure.py` |
| Output tokens (Anthropic ground truth) | `usage.output_tokens` from CLI JSON | extension |
| Input tokens, cache_read, cache_creation | `usage.*` from CLI JSON | extension |
| Wall-clock latency | `time.monotonic()` around subprocess | extension |
| API-side latency | `duration_api_ms` from CLI JSON | extension |
| Cost (informational) | `total_cost_usd` from CLI JSON | extension; Max sub absorbs cost |
| Concepts coverage | LLM-as-judge with hardcoded rubric, binary per concept | extension |
| Literal preservation | Regex over required quoted strings | extension |
| Format compliance | Regex (Hewn IR) + heuristics (Caveman style) | extension |
| Readability for non-tech | Persona-judge binary (T2 only) | extension |
| Multi-turn drift / hook value | T4 with explicit `--resume <session_id>` | extension |

What we deliberately **do not** claim or measure:
- Sonnet 4.6 or other models (Opus 4.7 only)
- Cross-provider (no GPT/Gemini)
- Human user studies
- Languages other than English
- Caveman's official `/caveman ultra` invocation (requires skill runtime
  not available under `--system-prompt`; we use a directive-based
  approximation labeled `caveman_full_plus_ultra_directive` — never
  called "Caveman Ultra" in the report)
- Pristine environment isolation (the user's `~/.claude/CLAUDE.md`
  remains active; impact calibrated by track T0)

## Track summary

| Track | Prompts | Runs | Arms | Calls | Purpose |
|---|---|---|---|---|---|
| T0  | short_en (10) | 1 | 4 | 40 | Append-vs-replace exposure calibration |
| T1a | short_en (10) | 1 | 3 | 30 | Strict Caveman parity (matches their `evals/llm_run.py`) |
| T1b | short_en (10) | 3 | 6 | 180 | Extended on Caveman's own prompts |
| T2  | vibe_en (5) | 3 | 6 | 90 | Non-tech user prompts |
| T3  | long_en (3, ~5k handbook) | 3 | 6 | 54 | Long context |
| T4  | multiturn (2 seq × 5 turns) | 2 | 5 | 100 | Drift + isolated hook value |
| T5  | expansive_en (2) | 2 | 6 | 24 | Honesty: where Hewn should NOT win |

## Arms

| ID | System prompt | Mechanism |
|---|---|---|
| `baseline` | (none) | `claude -p --model claude-opus-4-7 <prompt>` |
| `terse` | `"Answer concisely."` | `claude -p --model claude-opus-4-7 --system-prompt <content> <prompt>` |
| `caveman_full` | terse + Caveman SKILL.md (vendored, sha256 pinned) | same `--system-prompt` |
| `caveman_full_appended` | same content as caveman_full | `--append-system-prompt` |
| `caveman_full_plus_ultra_directive` | caveman_full + "Default intensity: ultra…" | `--system-prompt` |
| `terse_appended` | same as terse | `--append-system-prompt` |
| `hewn_prompt_only` | `hewn_thinking_system_prompt.txt` | `--append-system-prompt` |
| `hewn_full` | (same content via `--append`) + Python classifier hook | `hewn -p` real wrapper |

The Caveman SKILL.md is vendored under `caveman_source/` from the upstream
[juliusbrussee/caveman](https://github.com/juliusbrussee/caveman) repo at
commit `84cc3c14fa1e10182adaced856e003406ccd250d`, sha256 in metadata.

## Append-vs-replace asymmetry — what it means

`--system-prompt` REPLACES Claude Code's entire default system prompt
(tool instructions, env info, auto-memory, user CLAUDE.md).
`--append-system-prompt` ADDS to that stack.

Hewn arms use `--append`; Caveman/terse arms use `--system-prompt`.
This means Hewn arms inherit the user's `~/.claude/CLAUDE.md` (which
contains a terseness instruction) while Caveman/terse arms do not.

Causal claims:
- Hewn-vs-baseline (T1b-T5): both arms inherit default+CLAUDE.md → causal
- Hewn-vs-`caveman_full_appended` (cross-track join T0+T1b on short_en):
  both inherit default+CLAUDE.md → causal

Observational claims (cannot decompose default system prompt
contributions from user CLAUDE.md without `--bare`, which requires API key):
- Hewn-vs-stock-Caveman/terse on T2-T5

T0 calibrates the magnitude of the append-vs-replace exposure effect on
short_en. T1b reports both observed and appended-comparator pair.

## Reproduce

Prerequisites:
- `claude` CLI on PATH, authenticated (OAuth/Max subscription)
- Python 3.11+ with `tiktoken` installed (`pip install tiktoken`)

```bash
# 1. Smoke tests (validates env, ~30s)
python3 benchmarks/run.py --smoke

# 2. Full bench (sequential, ~70-100 min on Opus 4.7)
python3 benchmarks/run.py --track T0
python3 benchmarks/run.py --track T1a
python3 benchmarks/run.py --track T1b
python3 benchmarks/run.py --track T2
python3 benchmarks/run.py --track T3
python3 benchmarks/run.py --track T5
python3 benchmarks/run.py --track T4

# 3. Judge pass (~25-40 min)
python3 benchmarks/judge.py --track all

# 4. Generate REPORT.md
python3 benchmarks/measure.py
```

The harness is **idempotent** at the per-call level: if
`snapshots/raw/<track>/<arm>/<prompt_id>_r<N>.json` exists, the call is
skipped. Safe to interrupt and resume.

## Output layout

```
benchmarks/
├── prompts/                # all prompt sets + long handbook
├── rubrics/                # concepts.json (per-prompt required concepts), literals.json
├── arms/                   # one .txt per arm — content passed via --system-prompt
├── caveman_source/SKILL.md # vendored, sha256-attributed
├── snapshots/
│   ├── raw/<track>/<arm>/<prompt_id>_r<N>[_t<T>].json   # full claude -p JSON per call
│   ├── raw_judgments/<track>/<arm>/...                  # raw judge outputs + retry history
│   ├── judgments_<track>.json                           # parsed judge results
│   └── metadata.json       # CLI version, hewn commit, caveman sha256, seed, claude_md hash
└── report/
    ├── REPORT.md           # all tables, narrative, honesty box
    └── evidence/           # 6-8 side-by-side full-text examples (release proof)
```

## Methodology decisions captured during plan-review (Codex, 8 rounds)

The plan went through 8 cross-model review rounds with Codex before
execution. Notable decisions:

1. Use full model ID `claude-opus-4-7` (not `opus` alias) and assert
   `modelUsage["claude-opus-4-7"].outputTokens == usage.output_tokens`
   per call to reject samples that ran on a different model.
2. T1 split into T1a (strict Caveman replication: 1 run, 3 arms,
   tiktoken) and T1b (extended: 3 runs, 6 arms, both tokenizers).
3. Hook overhead measured via `cache_creation_input_tokens` delta, not
   `input_tokens` delta (verified empirically: hewn_full and
   hewn_prompt_only had identical `input_tokens=6`, but `cache_creation`
   differed by ~300 tokens per call).
4. T4 multi-turn uses explicit `--resume <session_id>` (never bare
   `--resume`). System prompt re-passed every turn (CLI does not persist
   it on resume — verified in smoke 4).
5. T4 includes `hewn_prompt_only` arm so hook value is isolated as
   `(hewn_prompt_only - hewn_full)` delta.
6. Arm-order randomization uses factoradic Lehmer code over
   `sha256("hewn-bench-v1:{prompt_id}:{run_index}")`. Reproducible
   across Python versions/machines.
7. `caveman_full_plus_ultra_directive` is OUR variant; never called
   "Caveman Ultra" (which requires skill runtime).
8. Environment NOT isolated (option B): user CLAUDE.md remains active.
   Asymmetry between `--system-prompt` (replace) and
   `--append-system-prompt` (add) calibrated by T0 on short_en.
9. T0 measures combined default+CLAUDE.md exposure, NOT CLAUDE.md alone
   (cannot isolate under OAuth — `--bare` requires API key).
10. Cross-track join for T1b (appended, observed) pair: appended side
    from T0 single-run, observed side from T1b median-of-3-runs.

Plan iteration files preserved at `/tmp/codex-review/plan-v{1..9}.md`
on the original benchmarking host.
