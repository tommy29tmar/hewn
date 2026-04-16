# SIGIL

[![CI](https://github.com/tommy29tmar/SIGIL/actions/workflows/ci.yml/badge.svg)](https://github.com/tommy29tmar/SIGIL/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-informational.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

**Compress the work, not just the words.**

SIGIL is a proposed reasoning IR for LLM workflows. The core idea is simple:

> compile first, expand second, explain last.

Provider status now lives on three rails:

- OpenAI: strongest focused micro benchmark evidence, and now positive on the harder extended selective matrix for both `gpt-5.4` and `gpt-5.4-mini`
- Anthropic: positive on starter `nano`, strongly positive on the harder extended selective matrix, and now validated again on a separate top-tier holdout with `claude-sonnet-4-6` and `claude-opus-4-6`
- Gemini: strongest current extended selective result, plus a much stronger macro+cache regime

The stable architecture is:

- provider-agnostic grammar, parser, repair, audit, and task compiler
- model-calibrated prompt families and routing profiles
- provider-specific transports only where the API surface really differs
- multiple compiled task contracts when one compact IR is not enough:
  - `nano` capsules for ultra-cheap routes
  - typed capsule-mini contracts when `nano` throws away too much structure
  - `targeted` compiled context when macro prompts need task-aware prefix compression

## Why People Pay Attention To This

Most token-compression projects stop at style compression. SIGIL is trying to
compress the actual work surface:

- task contracts
- transport format
- shared context
- provider- and model-specific routing

That makes the thesis stronger than “answer in fewer words.”

## Benchmark Snapshot

| Regime | Current strongest signal |
| --- | --- |
| OpenAI extended | `gpt-5.4-mini`: `11.03%` aggregate total-token savings |
| Anthropic extended | `claude-sonnet-4-20250514`: `28.37%` aggregate total-token savings |
| Anthropic holdout | `claude-opus-4-6`: `27.32%` aggregate total-token savings |
| Gemini extended | `gemini-2.5-flash`: `5.63%` aggregate total-token savings |
| Gemini macro cached | `47.24%` effective-total savings |

Full generated numbers live in [docs/results.md](docs/results.md).

This repository now contains both:

- the long-form project framing in [README_SIGIL.md](README_SIGIL.md)
- a minimal executable prototype for parsing, validating, and auditing SIGIL drafts

## What Is In This Repo

- [grammar/sigil.ebnf](grammar/sigil.ebnf): formal grammar for structured SIGIL documents
- [grammar/sigil_ascii.md](grammar/sigil_ascii.md): ASCII-safe operator aliases
- [prompts/system.txt](prompts/system.txt): prompt-only system prompt
- [prompts/hybrid_strict.txt](prompts/hybrid_strict.txt): strict hybrid-mode prompt for benchmarks
- [prompts/memory_strict.txt](prompts/memory_strict.txt): strict memory-mode prompt
- [prompts/compile_strict.txt](prompts/compile_strict.txt): strict compile-mode prompt
- [prompts/compiler.txt](prompts/compiler.txt): compile-mode prompt
- [prompts/audit.txt](prompts/audit.txt): audit decoder prompt
- [prompts/baseline_terse.txt](prompts/baseline_terse.txt): terse human-language baseline
- [prompts/debug_wire_schema.txt](prompts/debug_wire_schema.txt): compact wire-format debug prompt
- [prompts/architecture_wire_schema.txt](prompts/architecture_wire_schema.txt): compact wire-format architecture prompt
- [prompts/review_wire_schema.txt](prompts/review_wire_schema.txt): compact wire-format review prompt
- [prompts/refactor_wire_schema.txt](prompts/refactor_wire_schema.txt): compact wire-format refactor prompt
- [prompts/debug_wire_lite.txt](prompts/debug_wire_lite.txt): lighter debug wire prompt with local canonicalization
- [prompts/review_wire_lite.txt](prompts/review_wire_lite.txt): lighter review wire prompt with local canonicalization
- [prompts/architecture_wire_lite.txt](prompts/architecture_wire_lite.txt): lighter architecture wire prompt
- [prompts/refactor_wire_lite.txt](prompts/refactor_wire_lite.txt): lighter refactor wire prompt
- [.env.example](.env.example): local API configuration template
- [examples/](examples): example `draft`, `hybrid`, and `memory` documents
- [src/sigil/](src/sigil): stdlib-only parser, validator, and audit renderer
- [tests/](tests): regression tests for the prototype
- [evals/](evals): task corpus and offline measurement harness
- [profiles/](profiles): transport-routing profiles
- [docs/design.md](docs/design.md): scope of the current implementation
- [docs/roadmap.md](docs/roadmap.md): staged roadmap
- [docs/testing.md](docs/testing.md): how to test whether the skill actually works
- [docs/benchmarks.md](docs/benchmarks.md): early smoke-test results and current bottlenecks
- [docs/results.md](docs/results.md): generated provider benchmark matrix
- [docs/portability.md](docs/portability.md): generated contract-family portability matrix
- [docs/provider_strategy.md](docs/provider_strategy.md): provider-aware thesis and current optimization wall
- [docs/frontier.md](docs/frontier.md): stronger architecture directions beyond prompt-only SIGIL
- [docs/breakthroughs.md](docs/breakthroughs.md): external research directions that could move SIGIL toward a real serving/runtime breakthrough

## Current Status

What is real today:

- a prompt-only SIGIL contract
- a formalized grammar for structured outputs
- a parser/validator CLI for `.sigil` files
- a deterministic audit path from symbolic draft to human-readable summary

What remains research:

- learned symbolic nodes
- tokenizer adaptation
- latent or discrete reasoning backends
- total-cost reductions across models and providers

What now looks credible in practice:

- typed transport plus local render is more reliable than prompt-only freeform SIGIL
- `wire_lite` plus local canonicalization is the best current route to reducing input overhead
- `direct SIGIL` plus local repair is now viable when the task itself is precompiled into a micro capsule
- multi-IR routing is stronger than forcing one contract everywhere
- routed policies expose a real Pareto surface between total cost and semantic retention
- stronger models improve SIGIL markedly, but they also compress terse natural-language baselines better, so transfer between model families requires retuning

Latest benchmark signal now splits into two honest regimes.

Focused breakthrough rows:

- `gpt-5.4` targeted micro benchmark:
  - `parse_rate = 1.0`
  - `must_include_rate = 1.0`
  - `exact_literal_rate = 1.0`
  - `avg_total_tokens = 327` vs baseline `425.25`
  - total-token savings vs baseline: `18.72%`
  - latency savings vs baseline: `59.68%`
- `claude-sonnet-4-20250514` starter `nano`:
  - `parse_rate = 1.0`
  - `must_include_rate = 1.0`
  - `avg_total_tokens = 187.25` vs baseline `246`
  - aggregate total-token savings vs baseline: `23.88%`
- `claude-sonnet-4-6` top-tier holdout:
  - `parse_rate = 1.0`
  - `must_include_rate = 0.8958` vs baseline `0.5625`
  - `exact_literal_rate = 1.0` vs baseline `1.0`
  - `avg_total_tokens = 203` vs baseline `278.38`
  - aggregate total-token savings vs baseline: `27.08%`
  - latency savings vs baseline: `44.15%`
- `claude-opus-4-6` top-tier holdout:
  - `parse_rate = 1.0`
  - `must_include_rate = 0.8333` vs baseline `0.6354`
  - `exact_literal_rate = 0.8958` vs baseline `0.8958`
  - `avg_total_tokens = 204.88` vs baseline `281.88`
  - aggregate total-token savings vs baseline: `27.32%`
  - latency savings vs baseline: `28.21%`
- `gemini-2.5-flash` macro steady-state with explicit cache:
  - `parse_rate = 1.0`
  - `must_include_rate = 1.0`
  - `exact_literal_rate = 0.875`
  - `avg_effective_total_tokens = 174.25` vs baseline `277.5`
  - effective-total savings vs baseline: `36.59%`

Newest macro compiled-context rows:

- `gpt-5.4-mini` macro cold-start with focused compiled context:
  - `parse_rate = 1.0`
  - `must_include_rate = 0.9375` vs baseline `0.8750`
  - `exact_literal_rate = 0.9167` vs baseline `0.8750`
  - `avg_total_tokens = 1091.5` vs baseline `1191`
  - total-token savings vs baseline: `8.35%`
  - latency savings vs baseline: `14.38%`
- `claude-sonnet-4-20250514` macro cold-start with focused compiled context:
  - `parse_rate = 1.0`
  - `must_include_rate = 0.9375` vs baseline `0.5625`
  - `exact_literal_rate = 0.7500` vs baseline `0.7917`
  - `avg_total_tokens = 1164.75` vs baseline `1334.75`
  - total-token savings vs baseline: `12.74%`
  - latency savings vs baseline: `51.10%`
- `gemini-2.5-flash` macro cold-start with focused compiled context, `nano` task contracts, and `thinking_budget=0`:
  - `parse_rate = 1.0`
  - `must_include_rate = 0.8542` vs baseline `0.7292`
  - `exact_literal_rate = 0.7917` vs baseline `0.7917`
  - `avg_total_tokens = 1090.75` vs baseline `1216`
  - total-token savings vs baseline: `10.30%`
  - latency savings vs baseline: `24.09%`
- `gemini-2.5-flash` macro steady-state with cacheable compiled context, `nano` task contracts, and `thinking_budget=0`:
  - `parse_rate = 1.0`
  - `must_include_rate = 0.5833` vs baseline `0.4583`
  - `exact_literal_rate = 0.5000` vs baseline `0.7083`
  - `avg_total_tokens = 1677.25` vs baseline `1791.75`
  - total-token savings vs baseline: `6.39%`
  - `avg_effective_total_tokens = 122` vs baseline `231.25`
  - effective-total savings vs baseline: `47.24%`
  - latency savings vs baseline: `41.71%`

Latest selective extended matrix:

- `gpt-5.4` extended selective latest:
  - route: task-level multi-IR, with transferred `openai-gemini-nano` lanes on `review`, part of `debug`, and part of `architecture`, plus a tighter `cap56` debug lane, while `refactor` stays plain
  - `parse_rate = 1.0`
  - `must_include_rate = 0.7917` vs baseline `0.6901`
  - `exact_literal_rate = 0.9740` vs baseline `1.0`
  - `avg_total_tokens = 172.19` vs baseline `185.28`
  - aggregate total-token savings vs baseline: `7.07%`
  - aggregate latency savings vs baseline: `20.60%`
- `gpt-5.4-mini` extended selective latest:
  - route: selective SIGIL on most `debug`, most `review`, and part of `architecture`, with a tighter `cap56` debug lane and plain fallback still allowed
  - `parse_rate = 1.0`
  - `must_include_rate = 0.7083` vs baseline `0.5469`
  - `exact_literal_rate = 0.9583` vs baseline `0.9010`
  - `avg_total_tokens = 163.38` vs baseline `183.62`
  - aggregate total-token savings vs baseline: `11.03%`
  - aggregate latency savings vs baseline: `24.60%`
- `claude-sonnet-4-20250514` extended selective:
  - strongest current row is task-level routing with transfer-aware families plus `cap56` debug/refactor lanes
  - `parse_rate = 1.0`
  - `must_include_rate = 0.7448` vs baseline `0.5833`
  - `exact_literal_rate = 0.9219` vs baseline `0.8958`
  - `avg_total_tokens = 174.03` vs baseline `242.97`
  - aggregate total-token savings vs baseline: `28.37%`
  - aggregate latency savings vs baseline: `44.18%`
- `gemini-2.5-flash` extended selective:
  - strongest current row is task-level routing
  - `parse_rate = 1.0`
  - `must_include_rate = 0.7370` vs baseline `0.5495`
  - `avg_total_tokens = 150.75` vs baseline `159.75`
  - aggregate total-token savings vs baseline: `5.63%`
  - aggregate latency savings vs baseline: `11.95%`

The honest boundary is now clearer:

- SIGIL has clear win regimes, neutral regimes, and fallback-to-plain regimes
- the best shape is provider-specific and model-specific, not only provider-specific
- OpenAI now also has a new lever: cross-provider task-contract transfer, where `gemini-nano` contracts outperform older OpenAI-native compact prompts on `review`, a large share of `debug`, and part of `architecture`
- Anthropic now shows the same effect at larger scale: `gemini-transfer` lanes improve the harder extended matrix materially on `debug`, `review`, most `refactor`, and part of `architecture`
- a second new lever now compounds that: tighter per-lane output caps on already-winning families, especially `cap56` on OpenAI debug and Claude debug/refactor
- a third lever now compounds both: compiled shared context, which now wins on Gemini macro in both cold-start and cached steady-state regimes and is also positive on OpenAI mini and Claude cold-start
- `gpt-5.4` is still the strongest focused micro breakthrough, and now also clearly positive on the harder extended matrix
- `gpt-5.4-mini` is no longer an all-plain fallback case on the extended corpus
- `claude-sonnet-4` is strongest when SIGIL is used selectively, not universally, but it is no longer just “near parity”: it now has a clear extended breakthrough row too
- `gemini-2.5-flash` stays positive on the harder extended matrix, but its newer gains now come from routing, local repair, and compiled shared context rather than from a single dominant prompt family
- the best shape is provider-specific:
  - `gpt-5.4`: full SIGIL wins on the focused micro benchmark; selective architecture-only routing is the current honest extended result
  - `gpt-5.4-mini`: `selective` routing may collapse fully to plain baseline
  - `claude-sonnet-4`: starter `nano` can use full-route; extended selective prefers mostly plain plus one typed SIGIL lane
- `gemini-2.5-flash`: provider-specific ultra-short prompts plus stronger local repair now win on extended selective micro, macro cold-start, and macro cache regimes
- compiled shared context is now a real runtime lever:
  - `focused` compiled context is the current cold-start winner
  - `cacheable` compiled context is the current steady-state winner
- Gemini is no longer blocked at the API/config layer; the remaining question is how much quality we can recover while staying positive on total cost
- the repo now includes an extended 32-task micro corpus and a generated provider matrix so the benchmark can be published and rerun more systematically

## Quickstart

Install the package in editable mode:

```bash
python3 -m pip install -e .
```

Or with `uv`:

```bash
uv venv
uv pip install -e .
```

Validate a SIGIL document:

```bash
sigil validate examples/debugging.sigil
```

Inspect the parsed AST as JSON:

```bash
sigil parse examples/debugging.sigil --json
```

Render or reuse the audit view:

```bash
sigil audit examples/debugging.sigil
```

## Community

- start with [CONTRIBUTING.md](CONTRIBUTING.md)
- use [SUPPORT.md](SUPPORT.md) for the right support channel
- read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing
- cite the repo via [CITATION.cff](CITATION.cff) if you use it in research or derivative tooling

Inspect structural metrics:

```bash
sigil stats examples/debugging.sigil --json
```

Run the test suite:

```bash
python3 -m unittest discover -s tests -v
```

Run the sample eval harness:

```bash
python3 evals/measure.py evals/tasks.jsonl evals/sample_run.jsonl
```

Build the extended benchmark corpus:

```bash
sigil bench build-corpus --out-dir evals
```

Build macro tasks with a shared cache prefix:

```bash
sigil bench build-macro \
  evals/tasks_hybrid_micro.jsonl \
  evals/prefixes/service_context_v1.txt \
  evals/tasks_hybrid_macro.jsonl
```

Build macro tasks with a compiled shared context prefix:

```bash
sigil bench build-compiled-macro \
  evals/tasks_hybrid_nano.jsonl \
  evals/prefixes/service_context_v1.txt \
  evals/tasks_hybrid_macro_focused_nano.jsonl \
  --context-style focused
```

Render the published provider matrix:

```bash
sigil bench report evals/benchmark_matrix.json --out docs/results.md
```

Render the contract portability matrix:

```bash
sigil bench portability-report \
  evals/tasks_hybrid_nano_extended.jsonl \
  evals/runs/exp_gpt54mini_transfer_v2/gpt_5_4_mini_hybrid_multi_ir_extended_selective_efficiency.jsonl \
  evals/runs/exp_claude_transfer_v3/claude_sonnet_4_20250514_hybrid_multi_ir_extended_selective_efficiency.jsonl \
  evals/runs/exp_gpt54_openai_alt_v1/gpt_5_4_hybrid_multi_ir_extended_selective_efficiency.jsonl \
  evals/runs/multi_ir_gemini_ext_v1/gemini_2_5_flash_hybrid_task_extended_selective_efficiency_v1.jsonl \
  --out docs/portability.md
```

Build nano task capsules:

```bash
sigil bench build-capsules \
  evals/tasks_hybrid.jsonl \
  evals/tasks_hybrid_nano.jsonl \
  --style nano
```

Run a real benchmark via OpenAI Responses API:

```bash
python3 evals/run_openai.py \
  --tasks evals/tasks_hybrid.jsonl \
  --model gpt-5.2 \
  --out evals/runs/openai_gpt52_hybrid.jsonl \
  --variant baseline-terse@plain=prompts/baseline_terse.txt \
  --variant sigil-hybrid@structured=prompts/hybrid_strict.txt
```

The benchmark runner loads credentials from local `.env` by default.

To compare direct schema transport against a two-stage `draft2schema` lane:

```bash
python3 evals/run_openai.py \
  --tasks evals/tasks_debug.jsonl \
  --model gpt-4o-mini \
  --out evals/runs/debug_compare.jsonl \
  --variant sigil-debug@schema-debug_hybrid=prompts/debug_hybrid_schema.txt \
  --variant sigil-debug-d2s@draft2schema-debug_hybrid=prompts/hybrid_strict.txt::prompts/debug_hybrid_schema.txt
```

Then inspect both output compression and end-to-end cost:

```bash
python3 evals/measure.py evals/tasks_debug.jsonl evals/runs/debug_compare.jsonl --baseline sigil-debug
```

To compose a routed policy from several category-specific runs:

```bash
python3 evals/build_routed_run.py \
  evals/tasks_hybrid.jsonl \
  profiles/micro_router_v1.json \
  evals/runs/hybrid_routed_v1.jsonl \
  --source-run evals/runs/debug_wire_v1.jsonl \
  --source-run evals/runs/architecture_wire_v2.jsonl \
  --source-run evals/runs/review_wire_v1.jsonl \
  --source-run evals/runs/refactor_wire_v1.jsonl \
  --baseline-run evals/runs/hybrid_full_v2.jsonl
```

To auto-suggest a quality-first or efficiency-first router from observed runs:

```bash
python3 evals/suggest_profile.py \
  evals/tasks_hybrid.jsonl \
  profiles/auto_efficiency_router_v1.json \
  --objective efficiency \
  --run evals/runs/debug_wire_v1.jsonl \
  --run evals/runs/debug_wire_lite_v3.jsonl \
  --run evals/runs/architecture_wire_v2.jsonl \
  --run evals/runs/review_wire_v1.jsonl \
  --run evals/runs/review_wire_lite_v3.jsonl \
  --run evals/runs/refactor_wire_v1.jsonl
```

To let the baseline compete against SIGIL and produce a `selective` router:

```bash
python3 evals/suggest_profile.py \
  evals/tasks_hybrid_micro.jsonl \
  profiles/gpt_5_4_mini_selective_efficiency_router.json \
  --objective efficiency \
  --allow-plain-candidates \
  --name gpt_5_4_mini_micro_selective_efficiency_router \
  --run evals/runs/gpt_5_4_mini_sigil-debug-direct-compact.jsonl \
  --run evals/runs/gpt_5_4_mini_sigil-architecture-direct-compact-v4_r2.jsonl \
  --run evals/runs/gpt_5_4_mini_sigil-review-direct-compact.jsonl \
  --run evals/runs/gpt_5_4_mini_sigil-refactor-direct-compact-v4_r2.jsonl
```

To benchmark the compiler-first `direct SIGIL` lane on micro capsules:

```bash
python3 evals/build_task_capsules.py \
  evals/tasks_hybrid.jsonl \
  evals/tasks_hybrid_micro.jsonl \
  --style micro

python3 evals/run_openai.py \
  --tasks evals/tasks_debug_micro.jsonl \
  --model gpt-5.4 \
  --out evals/runs/gpt54_debug_direct_sigil_micro.jsonl \
  --variant sigil-debug-direct@sigil=prompts/debug_direct_sigil_micro.txt \
  --max-output-tokens 180 \
  --verbosity low
```

## Design Notes

The formal grammar in this repo intentionally covers structured SIGIL artifacts:

- `draft`
- `hybrid`
- `memory`
- `compile`

Pure `audit` mode is ordinary natural language and therefore lives outside the EBNF. The parser can still read a file whose header says `audit`, but the grammar itself is for the symbolic layer.

## Positioning

The main framing stays the same:

- SIGIL is not a novelty dialect
- SIGIL is a reasoning IR
- Caveman is a useful baseline for surface compression
- the serious claim is compiler-first task compression plus typed transport plus local rendering plus routing, not magic token savings

The full rationale, benchmark plan, scientific basis, and references remain in [README_SIGIL.md](README_SIGIL.md).
