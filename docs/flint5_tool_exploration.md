# Flint5-Tool Exploration — Research Notes

Status: **shelved, not shipped in main repo**.
Date: April 2026.
Target: Claude Opus 4.7 (`claude-opus-4-7`).

This document preserves the full exploration of using Anthropic tool_use
as an alternative transport for Flint's 5-slot IR, so a future maintainer
can resume if the conditions change. All code for this transport was
removed from `main` after measurement confirmed it does not belong in the
default user flow.

## Hypothesis

Instead of asking the model to emit `@flint v0 hybrid` text (the current
"text-sigil" transport), force it to call a tool `emit_flint` with an
input schema matching the 5 slots `G/C/P/V/A`. The server then serializes
the tool_input dict back to canonical `@flint` text.

Theoretical upsides:
1. Schema-guaranteed structure (no drift).
2. No wire scaffolding tokens emitted (`@flint v0 hybrid`, `G:`, `∧`).
3. Easier to validate.

## Measurement

Two benchmarks on `claude-opus-4-7`.

### Micro — `evals/tasks_top_tier_holdout.jsonl`

Short prompts (~266 tokens total input). Prompt cache threshold for
Opus 4.7 is 4096 tokens, so cache never activates here.

| cell | tokens | latency | must_include | sentinel |
|------|-------:|--------:|-------------:|---------:|
| text-sigil | 420 | 3.4s | 81% | 0 |
| flint5-tool | 2078 | 4.7s | 85% | 4/16 (25%) |

Tool-use loses hard: +395% input tokens (schema alone adds ~1400 tokens
per call, uncached), +38% latency. The +4pt coverage does not compensate.
25% sentinel rate on tasks where Opus invents dialect variations that
even repair heuristics cannot fix.

### Stress — `evals/tasks_stress_coding.jsonl`

Realistic coding session simulation (~18k tokens total input, cache_prefix
~10k tokens). Cache activates at 96% hit rate.

| cell | eff_tokens | latency | must_include | sentinel |
|------|-----------:|--------:|-------------:|---------:|
| text-sigil | 3769 | 4.0s | 76% | 0 |
| flint5-tool | 2665 | 4.9s | 81% | 0 |
| delta | **−29.3%** | +9% | +5.2pt | 0 |

Tool-use wins cleanly. Zero sentinels, 29% cheaper effective cost, modest
coverage advantage.

## Why the transition

- Micro: tool-schema cost (~1400 tokens input per call) is unamortizable.
  Cache threshold is 4096 tokens for Opus 4.7 (4.5, 4.6 also), so prompts
  under ~3500 tokens cannot cache the schema. Raw input cost dominates.
- Stress: cache carries the schema at 0.1× cost after first call. Output
  verbosity (tool mode emits ~2× the atoms per slot) is the only remaining
  gap, but becomes noise relative to total input.

## What unlocked the stress win

Five concrete fixes were required to reach 0 sentinels on stress:

1. **Schema tight**: `maxItems: 4` per slot, `maxLength: 40` per atom,
   plus a description with explicit call-syntax examples. Without these,
   Opus emits 6-atom slots with 100-char expressions.
2. **Coerce stringified arrays**: Opus occasionally returns
   `"C": '["async", "await", minimal_change, preserve_order]'` (string
   containing a mixed-quoted pseudo-array). A tolerant parser converts
   this to a real list.
3. **Category-aware serializer**: passing `task_category` to
   `repair_direct_flint_text` inside the serializer enables
   debugging/architecture/refactoring-specific rewrites (e.g.
   `_pass`/`_fail`/`_ok` outcome suffix, `ddl("12 weeks")` canonicalization).
4. **Comparator regex for numeric+letter suffixes**: `skew<=30s` was
   rewriting to `le(skew,30)s` (dangling `s`). Fixed by extending the
   comparator right-hand pattern to accept `[0-9]+(?:[A-Za-z]\w*)?`.
5. **List syntax normalizers**: `name[a|b|c]`, `name:a/b/c`, and `"x"/"y"`
   inside call args all rewrite to canonical comma form `name(a,b,c)`.

Some of these repair improvements are general-purpose and remain in
`src/flint/normalize.py` even after tool-use was shelved — they help
text-sigil on edge cases too.

## Why it was shelved

Flint's primary user surface is the Claude Code skill (`/flint <task>`
and the output-style). Skills produce **text**, not tool_use. The
`flint5-tool` transport requires the caller to be invoking the Anthropic
Messages API directly with `tool_choice: {"type": "tool", "name": "emit_flint"}`.

That means:
- **Claude Code skill users**: flint5-tool is unreachable. The `/flint`
  command cannot trigger tool_use because skills are text-generation only.
- **Direct-API integrators**: could benefit from the −29% long-context
  win, but this is a small audience relative to the skill audience.

The stress-bench win is real, but it is not portable to the primary user
flow. Shipping the tool-use transport in the default repo would add
complexity without matching upside.

## How to bring it back

Building an **MCP server** that exposes `emit_flint` as a tool that
Claude Code can call:

1. Server in Python using the `mcp` SDK, ~150-250 LOC. Handshake, tool
   declaration, call handler that runs `serialize_flint_from_tool_input`.
2. Install script that writes `~/.claude/mcp_servers.json` to register
   the server.
3. Updated skill that instructs Claude to call `emit_flint` via MCP.
4. An interactive experiment to measure compliance: unlike the
   Messages API, MCP has no `tool_choice: {"type":"tool",...}` forcing
   mechanism. The LLM chooses freely. If compliance drops below 85% we
   lose most of the measured advantage.

Estimated effort: 2-4 hours of development + a compliance spike on 10-15
real `/flint` invocations. **Do not proceed past the spike if compliance
falls below 85%.**

## Residual artifacts preserved in the repo

- `src/flint/normalize.py` — repair patches listed above (generally useful).
- `evals/tasks_stress_coding.jsonl` — long-context corpus for any future
  transport experiment.
- `scripts/build_stress_tasks.py` — reproducible corpus generator.
- `scripts/stress_table.py` — eff-tok comparison harness.

## Bench runs referenced in this document

Archived locations (not committed to git):
- `evals/runs/caveman/opus47_tool_r*.jsonl` — micro flint5-tool cell.
- `evals/runs/stress/opus47_stress_*_r*.jsonl` — stress cells for both
  text-sigil and flint5-tool.

If reproducing: the numbers above come from 4 runs × 4 tasks (micro) and
2 runs × 4 tasks (stress), on `claude-opus-4-7` with
`--cache-task-prefix --cache-system-prompt`, `max_tokens=512`.
