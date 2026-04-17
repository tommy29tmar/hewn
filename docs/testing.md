# Testing Flint

There are three distinct questions to test.

## 1. Does The Output Stay Inside The Representation?

This is the cheapest test.

Use:

```bash
flint validate examples/debugging.flint
flint stats examples/debugging.flint --json
```

For model outputs, save the output to a file and run the same commands. If parseability is unstable, the skill is not ready for automation.

## 2. Does Flint Compress Anything Useful?

Compare at least these variants on the same task set:

- plain assistant
- plain assistant with a concise prompt
- Flint with the strict mode-specific prompt

Use [evals/measure.py](../evals/measure.py) to measure:

- output token counts
- total token counts
- effective total token counts after subtracting cached input when reported
- reasoning token counts when the provider exposes them
- end-to-end elapsed time
- stage count for multi-pass transports
- clause count
- codebook size
- parse rate
- audit presence

Do not compare only against a verbose baseline. That would overstate the gain.

## 3. Does Quality Hold Up?

Compression without task retention is failure.

For each task, inspect whether the output:

- preserves critical literals
- captures the right goal and constraints
- proposes the right next action
- marks uncertainty honestly
- keeps verification visible

For coding tasks, the quickest serious check is:

1. generate Flint output
2. decode the audit
3. ask a human or a verifier model whether the recommended action is still correct

## Practical First Pass

The fastest honest first experiment is:

1. Use one model only.
2. Start with one mode only, preferably `hybrid`.
3. Use self-contained tasks, not vague prompts.
4. Collect both `baseline-terse` and `flint-hybrid`.
5. Measure with `evals/measure.py`.
6. Manually inspect the 5 biggest wins and the 5 worst failures.

That will tell you very quickly whether Flint is becoming an IR or just a formatting trick.

When you want a publishable snapshot instead of ad-hoc numbers, use:

```bash
flint bench report evals/benchmark_matrix.json --out docs/results.md
```

That report is now the canonical short summary of where Flint wins, where it only reaches parity, and where the wall still is.

## When To Use `draft2schema`

There is now a two-stage benchmark lane:

1. unconstrained Flint draft
2. schema-constrained final transport

This is useful to test whether a free draft improves structured quality enough to justify the extra pass.

Do not assume it helps.

Measure it against the direct schema lane on:

- `must_include_rate`
- `exact_literal_rate`
- `avg_total_tokens`
- `avg_elapsed_ms`

If the second stage does not buy back clear semantic quality, it should not be the default.

## When To Use A Router

If one transport is not best across all task families, stop forcing uniformity.

Build a routed benchmark instead:

- one category-specific run per task family
- one routing profile
- one composed run for comparison

The current repo already supports this with:

- [evals/build_routed_run.py](../evals/build_routed_run.py)
- [profiles/micro_router_v1.json](../profiles/micro_router_v1.json)
- [profiles/auto_efficiency_router_v3.json](../profiles/auto_efficiency_router_v3.json)
- [profiles/auto_quality_router_v3.json](../profiles/auto_quality_router_v3.json)
- [profiles/auto_balanced_router_v1.json](../profiles/auto_balanced_router_v1.json)

This is currently the most credible path from “interesting prompt” to “real transport policy”.

There is now a second control layer:

- [evals/build_adaptive_run.py](../evals/build_adaptive_run.py)

This lets you use:

- a compact primary run
- a richer fallback run
- a local verifier that promotes fallback only when parse, literal retention, or must-include coverage fail

Use it when:

- the compressed route wins often but is still brittle on a small subset of tasks
- you want “compress first, expand only if needed” instead of forcing the rich route everywhere

There is now also a generalized cascade form:

- ordered `candidate-run` tiers
- first verifier-passing tier wins
- later tiers are only evaluated locally, not sent back to the provider

This is the right shape when you want:

- `nano` first
- `wire-lite` second
- `capsule-mini` third
- `plain` last

The practical meaning of the current profiles is:

- `efficiency`: maximize visible compression and stay as close as possible to baseline total cost
- `balanced`: preserve task retention near baseline while still compressing the visible output aggressively
- `quality`: optimize retention first and accept higher input overhead

There is now a fourth practical pattern:

- `selective efficiency`: let Flint compete against the terse baseline per category, and keep Flint only where it wins
- `adaptive expansion`: let Flint try the cheapest route first, then expand only when the local verifier rejects the answer
- `cascaded adaptive expansion`: let Flint walk an ordered list of increasingly rich contracts and stop at the first acceptable output

Example:

```bash
flint bench build-adaptive-run evals/tasks_hybrid_micro_extended.jsonl evals/runs/adaptive.jsonl \
  --candidate-run evals/runs/nano.jsonl \
  --candidate-run evals/runs/wire_lite.jsonl \
  --candidate-run evals/runs/capsule_mini.jsonl \
  --candidate-run evals/runs/plain.jsonl \
  --baseline-run evals/runs/baseline.jsonl \
  --allow-repair \
  --min-must-include 0.75 \
  --min-exact-literal 0.75
```

## Can A Dedicated Codex Agent Replace The API?

Not for the serious benchmark.

A dedicated agent here can help with:

- generating sample outputs
- stress-testing parseability
- iterating on prompts quickly
- dry-running the eval pipeline

But it cannot replace a provider benchmark when you care about:

- billed output tokens
- reasoning token counts
- provider-specific reasoning controls
- exact behavior of the target model family

So the split is:

- use an internal agent for fast iteration
- use the API runner for the actual benchmark numbers

## Keep Benchmark Config Local

Keep API configuration inside this repo:

- store credentials in local `.env`
- keep `.env.example` as the checked-in template
- do not depend on another repo's runtime config

That keeps the benchmark reproducible and makes Flint portable as a standalone project.

## Provider-Aware Interpretation

Do not force one interpretation of “works” across all providers.

Use [docs/provider_strategy.md](provider_strategy.md) as the current rule:

- OpenAI and Claude should be judged on micro total cost
- Gemini should be judged on both micro raw total and macro steady-state effective total
- a provider-specific regime win is real, but it should be labeled as such
- when macro prompts are large but task-specific anchors are strong, prefer `targeted` compiled context over a generic focused prefix
- when macro prompts also depend on cache reuse, prefer `layered`: shared cacheable prefix plus targeted task overlay
- when `layered` still leaves too much uncached prompt budget, prefer `layered-needle`: shared cacheable prefix plus a smaller task overlay
