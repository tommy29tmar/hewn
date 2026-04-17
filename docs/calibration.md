# Model Calibration

Flint should be split into three layers:

## 1. Stable Core

These parts should stay mostly model-agnostic:

- grammar
- parser
- repair
- audit renderer
- task compiler

## 2. Calibrated Front-End

These parts should be calibrated per model family:

- direct Flint prompt family
- wire vs direct routing
- max output token caps
- literal-preservation bias

This is where `gpt-5.4` and `gpt-5.4-mini` diverged in practice.

## 3. Provider Integration

These parts are provider-specific:

- OpenAI Responses API harness
- Claude Code / Claude API integration
- system-prompt or project-file injection path
- cache behavior

## Why the mini model differs

`gpt-5.4-mini` compresses terse natural language well enough that Flint must be extremely cheap to beat it on total cost.

`gpt-5.4` has enough capacity to follow the symbolic contract more efficiently once the task is locally compiled, so Flint wins end-to-end.

That does **not** mean the project must choose one model forever. It means:

- keep the runtime stable
- calibrate the front-end per model
- store the result as a profile

## OpenAI calibration flow

```bash
python3 evals/calibrate_openai_model.py \
  --model gpt-5.4-mini \
  --objective efficiency \
  --overwrite
```

This script will:

1. run the baseline terse benchmark on micro tasks
2. run the candidate Flint transports
3. auto-suggest a profile
4. build a routed benchmark run
5. print the measured summary

If you want a `selective` router where the terse baseline can win some categories:

```bash
python3 evals/calibrate_openai_model.py \
  --model gpt-5.4-mini \
  --objective efficiency \
  --allow-plain-candidates \
  --overwrite
```

For the multi-IR extended workflow, you can now also route by task instead of by category:

```bash
python3 evals/calibrate_multi_ir_model.py \
  --provider anthropic \
  --model claude-sonnet-4-20250514 \
  --objective efficiency \
  --granularity task \
  --allow-plain-candidates \
  --overwrite
```

## Cache Reality Check

There is now a dedicated reporter:

```bash
python3 evals/cache_report.py \
  evals/runs/gpt_5_4_mini_selective_efficiency.jsonl \
  --provider openai \
  --model gpt-5.4-mini \
  --json
```

Use it before chasing caching as an optimization lever.

Current micro-benchmark reality:

- OpenAI `gpt-5.4` / `gpt-5.4-mini`: current prompts are far below the `1024`-token caching floor
- Anthropic Sonnet 4: current prompts are also far below the `1024`-token caching floor
- Gemini 2.5 Flash: current prompts are far below the `1024`-token caching floor

So caching is not the reason Flint wins today. The current wins come from a better transport/runtime, not from cache discounts.

For the current cross-provider snapshot, see:

- [docs/results.md](results.md)
- [docs/provider_strategy.md](provider_strategy.md)

## Claude Code flow

Claude Code is configurable via `CLAUDE.md` and `--append-system-prompt`, so Flint can be integrated there too. The right approach is not “reuse OpenAI prompts blindly”, but:

1. benchmark the chosen Claude model
2. produce a Claude-specific Flint profile
3. render that profile into `CLAUDE.md`

## Anthropic calibration flow

Anthropic is now wired through `evals/run_anthropic.py` and `evals/calibrate_anthropic_model.py`.

```bash
python3 evals/calibrate_anthropic_model.py \
  --model claude-sonnet-4-20250514 \
  --objective efficiency \
  --allow-plain-candidates \
  --overwrite
```

Current scope:

- plain baseline and direct Flint are supported
- prompt caching can be tested with `--cache-system-prompt`
- extended thinking can be tested with `--thinking-budget`
- schema transports are not first-class on Anthropic in this repo yet

## Gemini calibration flow

Gemini is now wired through `evals/run_gemini.py` and `evals/calibrate_gemini_model.py`.

```bash
python3 evals/calibrate_gemini_model.py \
  --model gemini-2.5-flash \
  --objective efficiency \
  --allow-plain-candidates \
  --thinking-budget 0 \
  --overwrite
```

Current scope:

- direct Flint is supported
- wire-lite schema transport is supported through a Gemini-compatible schema transform
- for `gemini-2.5-flash`, `--thinking-budget 0` is usually the right default for transport benchmarking
- `--allow-plain-candidates` is often the right mode on Gemini today, because selective routing materially narrows the total-cost gap

For Gemini micro specifically, there is now a second lever beyond transport choice:

- compress the task contract itself with `nano` capsules

Example:

```bash
flint bench build-capsules \
  evals/tasks_hybrid.jsonl \
  evals/tasks_hybrid_nano.jsonl \
  --style nano
```

This is what enabled the first positive Gemini micro result in the repo on aggregate total cost.

## Gemini macro flow

Gemini is the provider where `macro` benchmarking matters most, because explicit cached context can change the economics materially.

Build macro tasks from a long reusable prefix:

```bash
python3 evals/build_macro_tasks.py \
  evals/tasks_hybrid_micro.jsonl \
  evals/prefixes/service_context_v1.txt \
  evals/tasks_hybrid_macro.jsonl
```

Then run with explicit cache and steady-state latency:

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

Then route category-specific Flint runs and compare on `avg_effective_total_tokens`, not just raw total tokens.

## One Command To Publish The Current Matrix

The current benchmark matrix manifest lives in [evals/benchmark_matrix.json](../evals/benchmark_matrix.json).

Render it with:

```bash
flint bench report evals/benchmark_matrix.json --out docs/results.md
```
