# Provider Strategy

Flint should not be framed as a single compact language that wins unchanged across every provider.

The data in this repo supports a stronger and more honest claim:

> Flint is a transport runtime with a stable core and calibrated front-ends.

The newest result suggests an even stronger version:

> Flint works best as a multi-IR runtime, not as one compact notation.

And the newest macro evidence suggests an even more deployment-shaped extension:

> Flint should compile shared context too, not only task contracts and outputs.

That means four layers:

- stable core: grammar, parser, repair, audit, task compiler
- calibrated front-end: prompt family, transport shape, routing profile
- provider regime: micro vs macro, cached vs uncached, API-specific constraints
- input IR choice: `nano` capsules, typed capsule-mini contracts, compiled shared context, or plain baseline depending on category

## What “Parity” Actually Means

If the goal is “same efficiency or better on Claude and Gemini too”, parity cannot mean “one identical prompt wins everywhere”.

It has to mean:

- OpenAI has at least one clear positive benchmark regime and does not force Flint where it loses
- Claude is at least near-parity on the harder extended selective matrix and positive on starter `nano`
- Gemini reaches positive savings in a calibrated micro or macro regime

Today that is already true in a qualified way:

- `gpt-5.4`: strongly positive on the focused micro benchmark, and now clearly positive in aggregate on the harder task-level extended matrix
- `gpt-5.4-mini`: now materially positive as well on the harder task-level extended matrix once the router is allowed to use transferred `gemini-nano` lanes across debug, review, and part of architecture
- `gpt-5.4-mini`: now also positive on macro cold-start once the shared context is compiled first
- `claude-sonnet-4-20250514`: strongly positive on starter `nano`, and now strongly positive on the harder extended selective matrix too
- `claude-sonnet-4-20250514`: also positive on macro cold-start once the shared context is compiled first
- `claude-sonnet-4-6`: positive again on a separate harder 8-task holdout, which matters more than another win on the same tuning corpus
- `claude-opus-4-6`: also positive on that holdout, so the Anthropic story now reaches a real top-tier validation row
- `gemini-2.5-flash` with `nano` task contracts: positive on the harder extended selective matrix once the local repair/runtime is allowed to re-materialize the drafts correctly
- `gemini-2.5-flash`: also positive on macro steady-state effective total with explicit cache
- `gemini-2.5-flash`: now positive on macro cold-start and materially stronger on macro steady-state once the shared context itself is compiled

So the right industry claim is not:

> Flint beats terse natural language with one universal prompt.

It is:

> Flint beats terse natural language when the transport is calibrated to the provider and the benchmark matches the provider’s operating regime.

## Provider Playbook

## OpenAI

OpenAI is the cleanest case today.

- `gpt-5.4` prefers full Flint on the focused micro benchmark, and on the harder extended matrix it now reaches positive aggregate total savings with task-level routing:
  - `debug ->` transferred `openai-gemini-nano`, now often in `cap56` form on the tasks that clear the quality floor
  - `architecture -> capsule-mini` or transferred `openai-gemini-nano`
  - `review -> openai-gemini-nano` on the winning tasks
  - `refactor -> plain`
  - aggregate total-token savings vs baseline: `7.07%`
- `gpt-5.4-mini` now uses a real selective Flint share on the extended matrix and still stays below baseline on aggregate total cost:
  - `debug ->` mostly transferred `gemini-nano`, often with `cap56`
  - `review ->` mostly transferred `gemini-nano`
  - `architecture ->` mixed `gemini-nano`, `capsule-mini`, and plain
  - aggregate total-token savings vs baseline: `11.03%`
- Automatic caching is real, but irrelevant for the current micro benchmark because the contracts are too short.

Implication:

- use micro capsules aggressively
- keep full Flint on stronger models only when the benchmark actually supports it
- use transferred ultra-short contracts selectively when the task-level scorer says they beat plain
- keep selective or full plain fallback available on smaller models, but do not assume they must collapse to all-plain
- compiled shared context now looks worth carrying into OpenAI macro workloads too, at least for cold-start paths

## Claude

Claude is now the second clear proof-point for task-contract transfer.

As of April 16, 2026, the Anthropic Models API on this workspace exposes newer Anthropic targets including `claude-sonnet-4-6`, `claude-opus-4-6`, and `claude-opus-4-7`. Flint should therefore treat `claude-sonnet-4-6` as the current Sonnet target, not only the older `claude-sonnet-4-20250514` row.

- starter `nano` is strongly positive on total cost
- on the extended corpus, the strongest route is no longer mostly-plain:
  - `debugging ->` mostly `gemini-transfer`, now often in `cap56` form
  - `architecture ->` mixed `gemini-transfer`, `claude-nano`, and `capsule-mini`
  - `code_review ->` mostly `gemini-transfer`
  - `refactoring ->` almost entirely `gemini-transfer`, with `cap56` now winning much of the category
- forcing one single Flint lane is still not optimal
- but the front-end prompt contract is now more portable than before: some of the strongest Claude lanes are transferred from the Gemini family, not native Claude prompts
- aggregate total-token savings vs baseline on the current extended matrix: `28.37%`
- on a separate top-tier holdout, `claude-sonnet-4-6` now lands at:
  - `parse_rate = 1.0`
  - `avg_total_tokens = 203` vs baseline `278.38`
  - aggregate total-token savings vs baseline: `27.08%`
  - aggregate latency savings vs baseline: `44.15%`
- on the same holdout, `claude-opus-4-6` lands at:
  - `parse_rate = 1.0`
  - `avg_total_tokens = 204.88` vs baseline `281.88`
  - aggregate total-token savings vs baseline: `27.32%`
  - aggregate latency savings vs baseline: `28.21%`

Implication:

- optimize Claude as a selective transport target
- use `nano` task compilation when the caller can tolerate a more specialized contract
- use typed capsule-mini contracts when `nano` loses too much task structure
- do not force the OpenAI “all Flint” story onto Claude
- but do test cross-provider contract transfer aggressively, because Claude now benefits from it materially
- treat Claude as evidence that the runtime layer, not the prompt family alone, is what makes transfer work
- Claude also now benefits from compiled shared context on macro cold-start, which makes the architecture story stronger than “Gemini-only cache trick”

## Gemini

Gemini is the provider where regime matters the most.

Legacy micro reality:

- the old micro capsule benchmark was negative on raw total cost

Current extended selective reality:

- after rerendering direct Flint rows with the stronger local repair runtime
- after letting `nano` direct transports and capsule-mini compete together
- Gemini extended selective is now:
  - baseline: `159.75` avg total tokens
  - Flint routed: `150.16`
  - aggregate total-token savings: `6.01%`
  - aggregate latency savings: `30.32%`
  - `parse_rate = 1.0`
  - `must_include_rate = 0.6901` vs baseline `0.5495`

Macro reality:

- once the benchmark includes a long reusable prefix
- once explicit cache is enabled
- once one-time cache creation latency is excluded from steady-state measurement

Flint becomes clearly positive on effective total cost.

Newest macro reality:

- compiled shared context is now a first-class lever
- `focused` compiled context plus `nano` task contracts and `thinking_budget=0` is positive in cold-start:
  - `avg_total_tokens = 1090.75` vs baseline `1216`
  - aggregate total-token savings: `10.30%`
  - `must_include_rate = 0.8542` vs baseline `0.7292`
- `cacheable` compiled context plus `nano` task contracts and `thinking_budget=0` is the strongest steady-state Gemini row so far:
  - `avg_total_tokens = 1677.25` vs baseline `1791.75`
  - aggregate total-token savings: `6.39%`
  - `avg_effective_total_tokens = 122` vs baseline `231.25`
  - aggregate effective-total savings: `47.24%`
  - this beats the older long-prefix steady-state row on effective cost

Implication:

- Gemini should be positioned as both:
  - a `nano + selective` micro winner
  - a `macro + cache` winner
  - a `compiled-context` winner in both cold and warm regimes
- micro Gemini now depends on compressing the task contract as well as the response transport
- Gemini is currently the provider where compiled shared context has the clearest payoff

## Why This Is Still Valuable

This does not weaken Flint. It strengthens it.

If the repo claimed a universal compact prompt, it would be fragile and easy to falsify.

A provider-aware runtime is more credible because it matches how real inference systems are built:

- different tokenizers
- different cache floors
- different schema constraints
- different output styles
- different strength/latency tradeoffs

The real breakthrough is therefore architectural:

- compile the task locally
- choose the provider-optimal transport
- choose the category-optimal input IR
- when possible, choose the task-optimal transport, not only the category-optimal one
- render and audit deterministically
- measure the metric that matches the regime

## Current Wall

The main wall is now narrower and more specific:

- keeping positive total-token savings on the harder extended selective matrix for `gpt-5.4` while improving literal retention back toward the baseline ceiling
- understanding how far the new cross-provider prompt-transfer trick can be pushed before it overfits to the current corpus
- preserving very high literal retention on extended `debugging` and `architecture` corpora while using cheaper task contracts
- proving whether provider-side stop sequences are merely hygiene or can become a real cost lever

The newest concrete lever is task-level routing:

- Claude already moves from near-parity to clearly positive once routing is allowed to vary by task rather than only by category
- Gemini remains positive and becomes more retention-friendly
- OpenAI strong-tier is now meaningfully positive on aggregate total cost
- OpenAI mini is now positive too, which suggests that task-contract transfer plus local repair is a more general lever than we thought
- Claude is now positive enough on the extended selective matrix that it should be treated as a first-class breakthrough row, not only a supporting provider

One more constraint is now visible too:

- transfer is not symmetric
- `gemini-nano -> OpenAI` works
- `gemini-nano -> Claude` works
- `claude-nano -> Gemini` does not currently work on either `review` or `architecture`

That suggests some task contracts are simply better compile targets than others. Flint should therefore evolve toward a library of benchmarked transport contracts, not a one-prompt-per-provider story. The new [docs/portability.md](portability.md) report is the first explicit artifact for that thesis.

Everything else is no longer a conceptual blocker:

- parseability is industrial
- Gemini micro is positive with calibrated nano contracts
- Gemini macro is positive
- Gemini macro improves again once the shared prefix itself is compiled
- Claude starter `nano` is positive and Claude extended selective is now clearly positive as well
- OpenAI has a strong positive micro regime and now also positive extended selective rows on both `gpt-5.4` and `gpt-5.4-mini`

So the next work should not be generic prompt tweaking. It should be:

1. better `debug` and `architecture` nano transports for Claude and OpenAI strong-tier, because those are the categories where Flint still struggles under plain competition
2. multi-IR routing for Gemini micro, not just prompt-family tuning
3. a smarter scorer that can reward quality and latency separately from total-cost parity
4. bigger benchmark corpora
5. stable published reporting for micro vs macro
6. keeping claims aligned with the regime actually being measured
