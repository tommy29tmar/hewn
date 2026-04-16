# Evals

This directory gives you a minimal protocol to test whether SIGIL is doing useful work rather than merely producing exotic-looking output.

## Files

- [tasks.jsonl](tasks.jsonl): evaluation prompts and basic expectations
- [tasks_hybrid.jsonl](tasks_hybrid.jsonl): self-contained hybrid-mode tasks
- [tasks_memory.jsonl](tasks_memory.jsonl): memory-only tasks
- [tasks_compile.jsonl](tasks_compile.jsonl): compile-mode tasks
- [sample_run.jsonl](sample_run.jsonl): sample structured run against the included examples
- [measure.py](measure.py): offline measurer for structural validity and compression
- [cache_report.py](cache_report.py): report whether a run is even large enough for provider-side caching
- [build_extended_corpus.py](build_extended_corpus.py): generate a larger 32-task micro corpus
- [build_macro_tasks.py](build_macro_tasks.py): expand a task set with a long reusable cache prefix for macro benchmarks
- [benchmark_matrix.json](benchmark_matrix.json): manifest for the published provider matrix
- [build_task_capsules.py](build_task_capsules.py): generate `v1`, `micro`, or `nano` task capsules
- [run_openai.py](run_openai.py): real benchmark runner against the OpenAI Responses API
- [build_routed_run.py](build_routed_run.py): compose a routed benchmark run from multiple source runs
- [suggest_profile.py](suggest_profile.py): suggest a routing profile from benchmark runs
- [rerender_run.py](rerender_run.py): regenerate structured run content with the current local renderer
- [.env.example](../.env.example): local env template for API credentials
- [profiles/micro_router_v1.json](../profiles/micro_router_v1.json): current task-family routing policy

## Run The Sample

```bash
python3 evals/measure.py evals/tasks.jsonl evals/sample_run.jsonl
```

## Build The Extended Corpus

```bash
sigil bench build-corpus --out-dir evals
```

This creates:

- `evals/tasks_hybrid_micro_extended.jsonl`
- `evals/tasks_debug_micro_extended.jsonl`
- `evals/tasks_architecture_micro_extended.jsonl`
- `evals/tasks_review_micro_extended.jsonl`
- `evals/tasks_refactor_micro_extended.jsonl`

## Build Nano Capsules

```bash
sigil bench build-capsules \
  evals/tasks_hybrid.jsonl \
  evals/tasks_hybrid_nano.jsonl \
  --style nano
```

`nano` is currently most useful on Gemini micro, where compressing the task contract itself can change the total-cost result.

## Run A Real Test

1. Pick one baseline and one SIGIL variant.

Recommended:
- baseline: a plain concise prompt
- SIGIL: `prompts/hybrid_strict.txt`, `prompts/memory_strict.txt`, or `prompts/compile_strict.txt`

2. Prefer running one mode-specific task file at a time:

- [tasks_hybrid.jsonl](tasks_hybrid.jsonl)
- [tasks_memory.jsonl](tasks_memory.jsonl)
- [tasks_compile.jsonl](tasks_compile.jsonl)

3. Save outputs as JSONL rows like:

```json
{"task_id":"debug-auth-expiry","variant":"baseline-terse","model":"gpt-5.2","content":"Likely bug in auth middleware expiry handling...","usage":{"output_tokens":81,"reasoning_tokens":0}}
{"task_id":"debug-auth-expiry","variant":"sigil-hybrid","model":"gpt-5.2","content":"@sigil v0 hybrid\n...","usage":{"output_tokens":46,"reasoning_tokens":128}}
```

You can also store outputs in files and reference them by path:

```json
{"task_id":"debug-auth-expiry","variant":"sigil-hybrid","model":"gpt-5.2","path":"runs/debug-auth-expiry.sigil","usage":{"output_tokens":46,"reasoning_tokens":128}}
```

4. Measure the run:

```bash
python3 evals/measure.py evals/tasks.jsonl evals/runs/my_run.jsonl --baseline baseline-terse
```

## Run Directly Against OpenAI

Create a local `.env` from `.env.example` or export `OPENAI_API_KEY`, then run:

```bash
python3 evals/run_openai.py \
  --tasks evals/tasks_hybrid.jsonl \
  --model gpt-5.2 \
  --out evals/runs/openai_gpt52_hybrid.jsonl \
  --variant baseline-terse@plain=prompts/baseline_terse.txt \
  --variant sigil-hybrid@structured=prompts/hybrid_strict.txt \
  --reasoning-effort medium
```

The runner loads `.env` from the repo root by default, so no external project wiring is needed.

Then measure:

```bash
python3 evals/measure.py \
  evals/tasks_hybrid.jsonl \
  evals/runs/openai_gpt52_hybrid.jsonl \
  --baseline baseline-terse
```

For compile-mode and memory-mode benchmarks, swap in the corresponding task file and strict prompt.

## Run Against Anthropic

```bash
python3 evals/run_anthropic.py \
  --tasks evals/tasks_debug_micro.jsonl \
  --out evals/runs/claude_sonnet4_debug.jsonl \
  --model claude-sonnet-4-20250514 \
  --variant sigil-debug-direct-compact@sigil=prompts/debug_direct_sigil_compact.txt
```

## Run Against Gemini

```bash
python3 evals/run_gemini.py \
  --tasks evals/tasks_debug_micro.jsonl \
  --out evals/runs/gemini25flash_debug.jsonl \
  --model gemini-2.5-flash \
  --variant sigil-debug-direct-compact@sigil=prompts/debug_direct_sigil_compact.txt \
  --thinking-budget 0
```

For long benchmark runs, prefer enabling transient-provider retries:

```bash
python3 evals/calibrate_gemini_model.py \
  --model gemini-2.5-flash \
  --objective efficiency \
  --thinking-budget 0 \
  --max-retries 2 \
  --retry-backoff-seconds 2 \
  --overwrite
```

If you want a policy where SIGIL is used only when it beats the terse baseline for that category, add:

```bash
--allow-plain-candidates
```

## Render The Provider Matrix

Once the reference runs exist, render the current benchmark snapshot with:

```bash
sigil bench report evals/benchmark_matrix.json --out docs/results.md
```

The generated report is the shortest route to the current cross-provider picture:

- OpenAI positive in micro mode
- Claude positive in micro mode with selective routing
- Gemini negative on the old micro capsule, positive on `nano` micro aggregate total, and strongly positive in macro steady-state effective total with explicit cache

## Run Schema-First Benchmarks

Structured Outputs is useful when you want the model to fill a typed transport object and let the local runtime render valid SIGIL text.

Example:

```bash
python3 evals/run_openai.py \
  --tasks evals/tasks_hybrid.jsonl \
  --model gpt-4o-mini \
  --out evals/runs/hybrid_schema.jsonl \
  --variant sigil-hybrid-schema@schema-hybrid=prompts/hybrid_schema.txt
```

This uses:

- [schemas/hybrid_schema.json](../schemas/hybrid_schema.json)
- [prompts/hybrid_schema.txt](../prompts/hybrid_schema.txt)

The model produces JSON under the schema; the runner renders that JSON into SIGIL text before measurement.

## Run `draft2schema` Benchmarks

The runner also supports a two-stage lane:

1. a free SIGIL draft
2. a schema-constrained final transport conditioned on that draft

Example:

```bash
python3 evals/run_openai.py \
  --tasks evals/tasks_debug.jsonl \
  --model gpt-4o-mini \
  --out evals/runs/debug_d2s.jsonl \
  --variant sigil-debug@schema-debug_hybrid=prompts/debug_hybrid_schema.txt \
  --variant sigil-debug-d2s@draft2schema-debug_hybrid=prompts/hybrid_strict.txt::prompts/debug_hybrid_schema.txt
```

`evals/measure.py` will then report:

- `avg_total_tokens`
- `avg_effective_total_tokens`
- `avg_elapsed_ms`
- `avg_stage_count`

This makes it possible to compare semantic gain against real end-to-end cost.

## Build A Routed Benchmark

Once you have several category-specific runs, you can compose a routed policy:

```bash
python3 evals/build_routed_run.py \
  evals/tasks_hybrid.jsonl \
  profiles/micro_router_v1.json \
  evals/runs/hybrid_routed_v1.jsonl \
  --source-run evals/runs/debug_wire_v1.jsonl \
  --source-run evals/runs/architecture_wire_v2.jsonl \
  --source-run evals/runs/review_wire_v1.jsonl \
  --source-run evals/runs/refactor_wire_v1.jsonl \
  --baseline-run evals/runs/hybrid_full_v2.jsonl \
  --baseline-variant baseline-terse
```

Then measure the routed policy:

```bash
python3 evals/measure.py \
  evals/tasks_hybrid.jsonl \
  evals/runs/hybrid_routed_v1.jsonl \
  --baseline baseline-terse
```

## Suggest A Profile Automatically

To derive an efficiency-first, balanced, or quality-first router from observed runs:

```bash
python3 evals/suggest_profile.py \
  evals/tasks_hybrid.jsonl \
  profiles/auto_balanced_router_v1.json \
  --name auto_balanced_router_v1 \
  --objective balanced \
  --run evals/runs/debug_wire_v1.jsonl \
  --run evals/runs/debug_wire_lite_v3.jsonl \
  --run evals/runs/debug_capsule_named_v2.jsonl \
  --run evals/runs/architecture_schema_v4.jsonl \
  --run evals/runs/architecture_capsule_named_v2.jsonl \
  --run evals/runs/review_wire_lite_v3.jsonl \
  --run evals/runs/review_capsule_named_v2.jsonl \
  --run evals/runs/refactor_wire_lite_v1.jsonl \
  --run evals/runs/refactor_capsule_named_v2.jsonl
```

Current profile roles:

- `auto_efficiency_router_v3`: pushes visible compression hard and keeps total cost close to the terse baseline
- `auto_balanced_router_v1`: matches baseline `must_include_rate` while pushing `exact_literal_rate` to `1.0`
- `auto_quality_router_v3`: keeps the strongest semantic retention at a higher input-cost premium

For a pure efficiency profile:

```bash
python3 evals/suggest_profile.py \
  evals/tasks_hybrid.jsonl \
  profiles/auto_efficiency_router_v3.json \
  --name auto_efficiency_router_v3 \
  --objective efficiency \
  --run evals/runs/debug_wire_v1.jsonl \
  --run evals/runs/debug_wire_lite_v3.jsonl \
  --run evals/runs/architecture_wire_v2.jsonl \
  --run evals/runs/review_wire_v1.jsonl \
  --run evals/runs/review_wire_lite_v3.jsonl \
  --run evals/runs/refactor_wire_v1.jsonl
```

This produces a profile JSON plus per-category diagnostics.

To produce a `selective` efficiency router that may keep the baseline on some categories:

```bash
python3 evals/suggest_profile.py \
  evals/tasks_hybrid_micro.jsonl \
  profiles/gemini_2_5_flash_selective_efficiency_router.json \
  --name gemini_2_5_flash_micro_selective_efficiency_router \
  --objective efficiency \
  --allow-plain-candidates \
  --run evals/runs/gemini_2_5_flash_sigil-debug-direct-compact.jsonl \
  --run evals/runs/gemini_2_5_flash_sigil-architecture-direct-compact-v4.jsonl \
  --run evals/runs/gemini_2_5_flash_sigil-review-direct-compact.jsonl \
  --run evals/runs/gemini_2_5_flash_sigil-refactor-direct-compact.jsonl
```

To let the router choose per task instead of per category:

```bash
python3 evals/suggest_profile.py \
  evals/tasks_hybrid_nano_extended.jsonl \
  profiles/gemini_task_router_v1.json \
  --name gemini_task_router_v1 \
  --objective efficiency \
  --granularity task \
  --allow-plain-candidates \
  --run evals/runs/multi_ir_gemini_ext_v1/gemini_2_5_flash_baseline_hybrid_nano_extended.jsonl \
  --run evals/runs/multi_ir_gemini_ext_v1/gemini_2_5_flash_sigil-debug-gemini-nano_rerendered.jsonl \
  --run evals/runs/multi_ir_gemini_ext_v1/gemini_2_5_flash_sigil-architecture-capsule-mini72_rerendered.jsonl \
  --run evals/runs/multi_ir_gemini_ext_v1/gemini_2_5_flash_sigil-review-gemini-nano_rerendered.jsonl \
  --run evals/runs/multi_ir_gemini_ext_v1/gemini_2_5_flash_sigil-refactor-gemini-nano_rerendered.jsonl
```

`build_routed_run.py` now understands both:

- category profiles via `categories`
- task-level profiles via `tasks`

## Re-Render Structured Runs

If you changed only the local renderer or audit expansion logic, you do not need to pay for another API run.

Re-render existing structured outputs locally:

```bash
python3 evals/rerender_run.py \
  evals/runs/gpt54mini_review_plain_v2.jsonl \
  evals/runs/gpt54mini_review_plain_v3.jsonl
```

This keeps the original `usage` and `structured_data` but refreshes `content` with the current renderer.

## Cache-Aware Benchmarks

For repeated runs over the same SIGIL prefix, you can also pass:

```bash
--prompt-cache-key sigil-hybrid-v1 --prompt-cache-retention 24h
```

If the provider returns cached input usage, `evals/measure.py` reports `avg_cached_tokens`.

Before assuming caching should help, check whether the run is even cache-eligible:

```bash
python3 evals/cache_report.py \
  evals/runs/gpt_5_4_mini_selective_efficiency.jsonl \
  --provider openai \
  --model gpt-5.4-mini \
  --json
```

On the current micro benchmarks, all major providers come back as `too_small_for_cache`, which is why `cached_tokens` stays at zero.

For Gemini macro benchmarks, build a cache-eligible task set first:

```bash
python3 evals/build_macro_tasks.py \
  evals/tasks_hybrid_micro.jsonl \
  evals/prefixes/service_context_v1.txt \
  evals/tasks_hybrid_macro.jsonl
```

Then run with explicit cache:

```bash
python3 evals/run_gemini.py \
  --tasks evals/tasks_hybrid_macro.jsonl \
  --out evals/runs/gemini_2_5_flash_baseline_hybrid_macro_steady.jsonl \
  --model gemini-2.5-flash \
  --variant baseline-terse@plain=prompts/baseline_terse.txt \
  --thinking-budget 0 \
  --use-explicit-cache \
  --exclude-cache-create-latency \
  --cache-ttl 3600s
```

## What To Look At

The skill is working only if most of these hold at the same time:

- parse rate is high
- mode match rate is high
- must-include and exact-literal rates stay high
- output tokens drop versus the terse baseline
- total tokens do not explode enough to erase the gain
- effective total tokens after cache discounts improve when the provider actually returns cached input usage
- end-to-end latency stays acceptable for the workflow
- reasoning tokens do not explode enough to erase the gain
- audit summaries remain readable

## Minimum Success Bar

For an early prompt-only SIGIL test, a reasonable target is:

- `parse_rate >= 0.9`
- `mode_match_rate >= 0.9`
- `must_include_rate >= 0.9`
- `avg_token_savings_vs_baseline > 0.15`
- no obvious quality regressions on manual review

If token savings rise but parse rate or task quality falls, the skill is not working yet.
