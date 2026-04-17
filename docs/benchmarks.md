# Benchmark Notes

These are early smoke-test results, not publishable benchmark claims.

For the current generated matrix, see [docs/results.md](results.md).
For the provider-aware interpretation of those numbers, see [docs/provider_strategy.md](provider_strategy.md).

## Current Snapshot

### Top-tier holdout

This repo now also carries a separate harder holdout in [evals/tasks_top_tier_holdout.jsonl](../evals/tasks_top_tier_holdout.jsonl), deliberately kept apart from the main extended tuning loop. It contains 8 tasks:

- 2 debugging edge cases
- 2 architecture decisions with stronger compliance/ops pressure
- 2 review tasks with concrete exploit surfaces
- 2 refactor tasks with async/ordering constraints

Observed:

- `claude-sonnet-4-6`, routed holdout:
  - route: `debug/review/refactor -> gemini-transfer`, `architecture -> capsule-mini`
  - `parse_rate = 1.0`
  - `must_include_rate = 0.8958` vs baseline `0.5625`
  - `exact_literal_rate = 1.0` vs baseline `1.0`
  - `avg_total_tokens = 203` vs baseline `278.38`
  - aggregate total-token savings vs baseline: `27.08%`
  - aggregate latency savings vs baseline: `44.15%`
- `claude-opus-4-6`, routed holdout:
  - route: `debug/review/refactor -> gemini-transfer`, `architecture -> capsule-mini`
  - `parse_rate = 1.0`
  - `must_include_rate = 0.8333` vs baseline `0.6354`
  - `exact_literal_rate = 0.8958` vs baseline `0.8958`
  - `avg_total_tokens = 204.88` vs baseline `281.88`
  - aggregate total-token savings vs baseline: `27.32%`
  - aggregate latency savings vs baseline: `28.21%`

Interpretation:

- the Anthropic story now survives a holdout that was not used as the main tuning target
- the local repair/runtime matters more on the newer Anthropic models, because they drift into standalone `Flint:` labels and refactor pseudo-signatures more often
- once the compiler absorbs that drift, the token win still holds on both Sonnet-tier and Opus-tier Anthropic models

### Latest selective extended matrix

These are the current top-line rows after three important fixes:

- `allow-plain-candidates` now really lets the router choose `baseline-terse`
- `rerender_run.py` now re-materializes direct Flint rows with the latest local repair/runtime
- OpenAI extended calibration now also tests transferred `gemini-nano` prompt contracts for `review` and `architecture`

Observed on `evals/tasks_hybrid_nano_extended.jsonl`:

- `gpt-5.4`, selective extended latest:
  - route: task-level multi-IR with `review -> openai-gemini-nano`, part of `debug -> openai-gemini-nano-cap56`, `architecture -> capsule-mini` or `openai-gemini-nano`, `refactor -> plain`
  - `parse_rate = 1.0`
  - `must_include_rate = 0.7917` vs baseline `0.6901`
  - `exact_literal_rate = 0.9740` vs baseline `1.0`
  - `avg_total_tokens = 172.19` vs baseline `185.28`
  - aggregate total-token savings vs baseline: `7.07%`
  - aggregate latency savings vs baseline: `20.60%`
- `gpt-5.4-mini`, selective extended latest:
  - route: task-level selective with transferred `gemini-nano` on most `debug`, most `review`, and part of `architecture`, with `debug` now often using `cap56`
  - `parse_rate = 1.0`
  - `must_include_rate = 0.7083` vs baseline `0.5469`
  - `exact_literal_rate = 0.9583` vs baseline `0.9010`
  - `avg_total_tokens = 163.38` vs baseline `183.62`
  - aggregate total-token savings vs baseline: `11.03%`
  - aggregate latency savings vs baseline: `24.60%`
- `claude-sonnet-4-20250514`, selective extended latest:
  - route: task-level multi-IR with `gemini-transfer` on most `debug`, most `review`, almost all `refactor`, and part of `architecture`, with `cap56` now winning in `debug` and much of `refactor`
  - `parse_rate = 1.0`
  - `must_include_rate = 0.7448` vs baseline `0.5833`
  - `exact_literal_rate = 0.9219` vs baseline `0.8958`
  - `avg_total_tokens = 174.03` vs baseline `242.97`
  - aggregate total-token savings vs baseline: `28.37%`
  - aggregate latency savings vs baseline: `44.18%`
- `gemini-2.5-flash`, selective extended `v2`:
  - route: `debug/review/refactor -> nano direct`, `architecture -> capsule-mini`
  - `parse_rate = 1.0`
  - `must_include_rate = 0.6901` vs baseline `0.5495`
  - `avg_total_tokens = 150.16` vs baseline `159.75`
  - aggregate total-token savings vs baseline: `6.01%`
  - aggregate latency savings vs baseline: `30.32%`

Interpretation:

- the most honest benchmark is no longer “best Flint prompt wins”, but “what does the router choose when plain is a valid option?”
- the newest OpenAI lift comes from cross-provider task-contract transfer: `gemini-nano` is now a winning OpenAI lane on `review`, much of `debug`, and part of `architecture`
- a second lift now compounds that: aggressive `cap56` variants improve already-winning debug/refactor lanes without changing the core transport family
- the same transfer idea now works on Claude too, and there it improves the full extended routed matrix materially across `debug`, `review`, and `refactor`
- architecture is still the category where Flint survives hardest competition most consistently
- Gemini benefited the most from the stronger local repair/runtime
- the smaller OpenAI model is no longer an all-plain fallback case on the harder extended corpus

### Task-level routing on the extended matrix

We then replaced category routing with task-level routing, and later re-ran OpenAI with transferred `gemini-nano` lanes plus stronger local repair.

Observed:

- `claude-sonnet-4-20250514`, task-level extended latest:
  - `parse_rate = 1.0`
  - `must_include_rate = 0.7526` vs baseline `0.5833`
  - `exact_literal_rate = 0.9219` vs baseline `0.8958`
  - `avg_total_tokens = 177.78` vs baseline `242.97`
  - aggregate total-token savings vs baseline: `26.83%`
  - aggregate latency savings vs baseline: `44.72%`
  - route learned:
    - `debug -> gemini-transfer` on most tasks
    - `review -> gemini-transfer` on most tasks
    - `architecture -> gemini-transfer` on a meaningful subset, otherwise `claude-nano` or `capsule-mini`
    - `refactor -> gemini-transfer` on almost every task
- `gemini-2.5-flash`, task-level extended `v1`:
  - `parse_rate = 1.0`
  - `must_include_rate = 0.7370` vs baseline `0.5495`
  - `avg_total_tokens = 150.75` vs baseline `159.75`
  - aggregate total-token savings vs baseline: `5.63%`
  - aggregate latency savings vs baseline: `11.95%`
- `gpt-5.4`, task-level extended latest:
  - `parse_rate = 1.0`
  - `must_include_rate = 0.7839` vs baseline `0.6901`
  - `exact_literal_rate = 0.9896` vs baseline `1.0`
  - `avg_total_tokens = 173.88` vs baseline `185.28`
  - aggregate total-token savings vs baseline: `6.16%`
  - aggregate latency savings vs baseline: `19.48%`
  - route learned:
    - `debug -> openai-gemini-nano` on a meaningful subset
    - `architecture -> capsule-mini` or transferred `openai-gemini-nano`
    - `review -> openai-gemini-nano` on the winning tasks
    - `refactor -> plain`
- `gpt-5.4-mini`, task-level extended latest:
  - `parse_rate = 1.0`
  - `must_include_rate = 0.7083` vs baseline `0.5469`
  - `exact_literal_rate = 0.9583` vs baseline `0.9010`
  - `avg_total_tokens = 165.97` vs baseline `183.62`
  - aggregate total-token savings vs baseline: `9.62%`
  - aggregate latency savings vs baseline: `19.23%`

Interpretation:

- per-task routing is the first controller-level change that materially moves the frontier, especially on Claude
- cross-provider task-contract transfer is now the second controller-level change that materially moves the frontier, especially on OpenAI and Claude
- Gemini stays positive under both category routing and task routing, but task routing buys more retention than raw savings
- OpenAI strong-tier is now clearly positive once `review` and part of `architecture` switch to transferred `gemini-nano` task contracts
- OpenAI mini is now positive as well on the harder extended matrix, which is the strongest sign so far that task-contract transfer is a real lever rather than a one-off prompt trick

### Stop-sequence experiment

We also added provider-side stop sequences for direct Flint on Anthropic and Gemini.

Current reading:

- the change is low-risk and worth keeping in the runtime
- it has not yet produced a standalone breakthrough row
- the main gains still come from better routing and better task contracts, not from stop sequences alone

### `memory` mode

Run:

- task file: `evals/tasks_memory.jsonl`
- prompt: `prompts/memory_strict.txt`
- model: `gpt-5.2`
- reasoning effort: `none`

Observed:

- `parse_rate = 1.0`
- `mode_match_rate = 1.0`
- `avg_output_tokens = 50`
- `avg_reasoning_tokens = 0`

Interpretation:

- memory compression is already stable enough to benchmark further
- the current representation works well for compact persistent constraints

### `hybrid` mode

Run:

- task file: `evals/tasks_hybrid.jsonl`
- prompt: `prompts/hybrid_strict.txt`
- model: `gpt-5.2`
- reasoning effort: `none`
- smoke task: `debug-auth-expiry`

Observed:

- baseline terse: `450` output tokens, `0` reasoning tokens
- Flint hybrid: `193` output tokens, `0` reasoning tokens
- `parse_rate = 1.0`
- `mode_match_rate = 1.0`
- token savings vs baseline: about `57%`

Interpretation:

- strict symbolic prompting can already beat a terse natural-language baseline on output size
- the most important gain came from making the task self-contained and tightening syntax rules

### `hybrid` mode, 4-task set

Run:

- task file: `evals/tasks_hybrid.jsonl`
- prompt: `prompts/hybrid_strict.txt`
- model: `gpt-5.2`
- reasoning effort: `none`

Observed:

- baseline terse average: `235` output tokens
- Flint hybrid average: `164.75` output tokens
- raw `parse_rate = 0.75`
- repaired `repair_parse_rate = 1.0`
- raw token savings vs baseline: about `19%`
- `avg_reasoning_tokens = 0`

Interpretation:

- one prompt already generalizes across debugging, architecture, security review, and refactor tasks
- the remaining failures are near-miss syntax drifts, not deep semantic collapse
- the local repair layer is therefore worth keeping as part of the runtime, but raw parse rate still needs improvement

### Provider matrix, micro routed runs

Runs:

- task file: `evals/tasks_hybrid_micro.jsonl`
- objective: `efficiency`
- routing: provider-specific calibrated profile

Observed:

- `gpt-5.4` routed Flint beats the original natural-language baseline end-to-end:
  - `parse_rate = 1.0`
  - `must_include_rate = 1.0`
  - `exact_literal_rate = 1.0`
  - `avg_total_tokens = 327` vs baseline `425.25`
  - latency savings vs baseline: about `59.68%`
- `gpt-5.4-mini` selective efficiency routing is now clearly positive on total cost:
  - `parse_rate = 1.0`
  - `must_include_rate = 0.75`
  - `exact_literal_rate = 1.0`
  - `avg_total_tokens = 237.75` vs baseline `269.5`
  - total-token savings vs baseline: about `10.93%`
  - latency savings vs baseline: about `31.97%`
- `claude-sonnet-4-20250514` selective efficiency routing also beats the terse baseline on total cost:
  - `parse_rate = 1.0`
  - `must_include_rate = 0.9375`
  - `exact_literal_rate = 1.0`
  - `avg_total_tokens = 280.75` vs baseline `306`
  - total-token savings vs baseline: about `7.29%`
  - latency savings vs baseline: about `19.73%`
- `gemini-2.5-flash` selective efficiency routing is materially better than all-Flint routing, but still loses on total cost:
  - `parse_rate = 1.0`
  - `must_include_rate = 0.6875`
  - `exact_literal_rate = 0.875`
  - `avg_total_tokens = 236` vs baseline `215.5`
  - total-token savings vs baseline: about `-11.14%`
  - latency savings vs baseline: about `7.48%`

### `claude-sonnet-4-20250514`, micro tasks with `nano` task capsules

Starter run:

- tasks: `evals/tasks_hybrid_nano.jsonl`
- profile: `profiles/claude_sonnet_4_20250514_nano_efficiency_router_v1.json`
- run: `evals/runs/claude_sonnet_4_20250514_hybrid_nano_efficiency_v1.jsonl`

Observed:

- baseline terse nano:
  - `avg_total_tokens = 246`
  - `must_include_rate = 0.6875`
  - `exact_literal_rate = 0.7083`
- Flint full-route nano:
  - `parse_rate = 1.0`
  - `must_include_rate = 1.0`
  - `exact_literal_rate = 0.875`
  - `avg_total_tokens = 187.25`
  - aggregate total-token savings vs baseline: about `23.88%`
  - aggregate latency savings vs baseline: about `40.65%`

Extended run:

- tasks: `evals/tasks_hybrid_nano_extended.jsonl`
- profile: `profiles/claude_sonnet_4_20250514_multi_ir_extended_efficiency_router_v1.json`
- run: `evals/runs/claude_sonnet_4_20250514_hybrid_multi_ir_extended_efficiency_v1.jsonl`

Observed:

- baseline terse nano extended:
  - `avg_total_tokens = 245.12`
  - `must_include_rate = 0.6042`
  - `exact_literal_rate = 0.9062`
- Flint multi-IR extended:
  - `parse_rate = 0.9375`
  - `must_include_rate = 0.8073`
  - `exact_literal_rate = 0.849`
  - `avg_total_tokens = 213.88`
  - aggregate total-token savings vs baseline: about `12.75%`
  - aggregate latency savings vs baseline: about `51.65%`

Interpretation:

- Claude benefits from the same structural idea that unlocked Gemini: compress the task contract, not only the response
- full-route Flint is already strong on the starter nano set
- on the extended set, the best Claude policy is now multi-IR:
- typed capsule-mini for `debugging`
- typed capsule-mini for `architecture`
- nano direct Flint for `code_review`
- nano direct Flint for `refactoring`

### `gemini-2.5-flash`, micro tasks with `nano` task capsules

Run:

- tasks: `evals/tasks_hybrid_nano.jsonl`
- builder: `flint bench build-capsules ... --style nano`
- routed profile: `profiles/gemini_2_5_flash_gemini_nano_efficiency_router_v1.json`

Observed:

- baseline terse nano:
  - `avg_total_tokens = 183`
  - `must_include_rate = 0.5833`
- Flint routed nano:
  - `parse_rate = 1.0`
  - `must_include_rate = 0.7292`
  - `exact_literal_rate = 0.8333`
  - `avg_total_tokens = 117`
  - aggregate total-token savings vs baseline: about `36.07%`
  - aggregate latency savings vs baseline: about `2.48%`

Interpretation:

- the next real frontier was not only output transport
- compressing the task capsule itself changes Gemini micro economics materially
- this is the first strong micro-regime Gemini result in the repo that is positive on aggregate total cost without relying on cache

### `gemini-2.5-flash`, extended micro tasks with `nano` task capsules

Run:

- tasks: `evals/tasks_hybrid_nano_extended.jsonl`
- builder: `flint bench build-capsules ... --style nano`
- routed profile: `profiles/gemini_2_5_flash_gemini_nano_extended_efficiency_router_v1.json`

Observed:

- baseline terse nano extended:
  - `avg_total_tokens = 160.25`
  - `must_include_rate = 0.5469`
  - `exact_literal_rate = 0.8646`
- Flint routed nano extended:
  - `parse_rate = 0.9583`
  - `must_include_rate = 0.5807`
  - `exact_literal_rate = 0.7708`
  - `avg_total_tokens = 132.84`
  - aggregate total-token savings vs baseline: about `17.10%`
  - aggregate latency savings vs baseline: about `30.9%`

Interpretation:

- Gemini micro is no longer only a starter-set success
- the positive result survives on the extended corpus once task capsules and prompts are both provider-compressed

### `gemini-2.5-flash`, macro tasks with explicit cache

Run:

- tasks: `evals/tasks_hybrid_macro.jsonl`
- builder: `evals/build_macro_tasks.py`
- prefix: `evals/prefixes/service_context_v1.txt`
- runner: `evals/run_gemini.py`
- options: `--use-explicit-cache --exclude-cache-create-latency`
- routed profile: `profiles/gemini_2_5_flash_macro_selective_efficiency_router.json`

Observed:

- baseline terse:
  - `avg_input_tokens = 1772.5`
  - `avg_cached_tokens = 1700`
  - `avg_effective_total_tokens = 277.5`
- Flint routed:
  - `parse_rate = 1.0`
  - `must_include_rate = 1.0`
  - `exact_literal_rate = 0.875`
  - `avg_input_tokens = 1906.5`
  - `avg_cached_tokens = 1834`
  - `avg_effective_total_tokens = 174.25`
  - `avg_output_tokens = 101.75`
  - `avg_elapsed_ms = 1925.16` vs baseline `2475.12`
- comparison:
  - raw total tokens are roughly flat: `2008.25` vs baseline `1977.5`
  - effective total tokens improve by about `36.59%`
  - latency improves by about `5.08%`

Interpretation:

- Gemini was not fundamentally “bad for Flint”; the micro benchmark was simply too small for caching to matter
- once the task is moved into a realistic cached-prefix regime, Flint plus routing starts to win materially on effective cost
- for Gemini, the architectural lesson is stronger than for the other providers:
  - micro tasks need ultra-cheap transports
  - macro tasks need explicit cached context and steady-state measurement

### `gemini-2.5-flash`, macro focused compiled context, cold-start

Run:

- tasks: `evals/tasks_hybrid_macro_focused_nano.jsonl`
- builder: `evals/build_compiled_macro_tasks.py`
- prefix source: `evals/prefixes/service_context_v1.txt`
- context style: `focused`
- task source: `evals/tasks_hybrid_nano.jsonl`
- runner: `evals/run_gemini.py`
- options: `--thinking-budget 0`
- routed profile: `profiles/experimental/gemini_2_5_flash_macro_focused_nano_tb0_efficiency_router_v1.json`

Observed:

- baseline terse:
  - `avg_input_tokens = 1025.75`
  - `avg_total_tokens = 1216`
  - `avg_output_tokens = 190.25`
- Flint routed:
  - `parse_rate = 1.0`
  - `must_include_rate = 0.8542` vs baseline `0.7292`
  - `exact_literal_rate = 0.7917` vs baseline `0.7917`
  - `avg_input_tokens = 1020.5`
  - `avg_total_tokens = 1090.75`
  - `avg_output_tokens = 70.25`
  - `avg_elapsed_ms = 1380.4` vs baseline `1818.49`
- comparison:
  - aggregate total-token savings vs baseline: `10.30%`
  - aggregate latency savings vs baseline: `24.09%`

Interpretation:

- compiled shared context is now strong enough to make Gemini macro positive even without cache
- the gain is not just shorter visible output; the whole cold-start request gets cheaper
- the strongest cold-start recipe so far is:
  - compile the shared context
  - shrink the task contract to `nano`
  - drop thinking budget to zero
  - route selectively

### `gemini-2.5-flash`, macro cacheable compiled context, steady-state

Run:

- tasks: `evals/tasks_hybrid_macro_cacheable_nano.jsonl`
- builder: `evals/build_compiled_macro_tasks.py`
- prefix source: `evals/prefixes/service_context_v1.txt`
- context style: `cacheable`
- task source: `evals/tasks_hybrid_nano.jsonl`
- runner: `evals/run_gemini.py`
- options: `--thinking-budget 0 --use-explicit-cache --exclude-cache-create-latency`
- routed profile: `profiles/experimental/gemini_2_5_flash_macro_cacheable_nano_tb0_balanced_manual_v1.json`

Observed:

- baseline terse:
  - `avg_input_tokens = 1593.5`
  - `avg_cached_tokens = 1560.5`
  - `avg_total_tokens = 1791.75`
  - `avg_effective_total_tokens = 231.25`
  - `avg_output_tokens = 198.25`
- Flint routed:
  - `parse_rate = 1.0`
  - `must_include_rate = 0.5833` vs baseline `0.4583`
  - `exact_literal_rate = 0.5000` vs baseline `0.7083`
  - `avg_input_tokens = 1588.25`
  - `avg_cached_tokens = 1555.25`
  - `avg_total_tokens = 1677.25`
  - `avg_effective_total_tokens = 122`
  - `avg_output_tokens = 89`
  - `avg_elapsed_ms = 1024.76` vs baseline `1758.17`
- comparison:
  - aggregate total-token savings vs baseline: `6.39%`
  - aggregate effective-total savings vs baseline: `47.24%`
  - aggregate latency savings vs baseline: `41.71%`

Interpretation:

- compiled shared context is now the strongest steady-state Gemini lever in the repo
- the new row beats the earlier long-prefix cache row on effective cost
- it also beats the compiled plain baseline on raw total, which is the stronger claim
- for Gemini macro, the current best stack is:
  - cacheable compiled context
  - `nano` task contracts
  - `thinking_budget=0`
  - selective routing with plain still allowed where quality would collapse

### `gpt-5.4-mini`, macro focused compiled context, cold-start

Run:

- tasks: `evals/tasks_hybrid_macro_focused_nano.jsonl`
- builder: `evals/build_compiled_macro_tasks.py`
- prefix source: `evals/prefixes/service_context_v1.txt`
- context style: `focused`
- task source: `evals/tasks_hybrid_nano.jsonl`
- runner: `evals/run_openai.py`
- options: `--reasoning-effort none --verbosity low`
- routed profile: `profiles/experimental/gpt_5_4_mini_macro_focused_nano_efficiency_router_v1.json`

Observed:

- baseline terse:
  - `avg_input_tokens = 990.25`
  - `avg_total_tokens = 1191`
  - `avg_output_tokens = 200.75`
- Flint routed:
  - `parse_rate = 1.0`
  - `must_include_rate = 0.9375` vs baseline `0.8750`
  - `exact_literal_rate = 0.9167` vs baseline `0.8750`
  - `avg_input_tokens = 984.25`
  - `avg_total_tokens = 1091.5`
  - `avg_output_tokens = 107.25`
  - `avg_elapsed_ms = 2448.35` vs baseline `2859.70`
- comparison:
  - aggregate total-token savings vs baseline: `8.35%`
  - aggregate latency savings vs baseline: `14.38%`

Interpretation:

- compiled shared context is not only a Gemini lever
- on OpenAI mini, it produces a real cold-start win even without relying on cache
- the winning stack is:
  - focused compiled context
  - transferred `gemini-nano` on debug/review/architecture
  - `cap56` on debug
  - plain fallback on refactor

### `claude-sonnet-4-20250514`, macro focused compiled context, cold-start

Run:

- tasks: `evals/tasks_hybrid_macro_focused_nano.jsonl`
- builder: `evals/build_compiled_macro_tasks.py`
- prefix source: `evals/prefixes/service_context_v1.txt`
- context style: `focused`
- task source: `evals/tasks_hybrid_nano.jsonl`
- runner: `evals/run_anthropic.py`
- routed profile: `profiles/experimental/claude_sonnet_4_20250514_macro_focused_nano_efficiency_router_v1.json`

Observed:

- baseline terse:
  - `avg_input_tokens = 1099.75`
  - `avg_total_tokens = 1334.75`
  - `avg_output_tokens = 235`
- Flint routed:
  - `parse_rate = 1.0`
  - `must_include_rate = 0.9375` vs baseline `0.5625`
  - `exact_literal_rate = 0.7500` vs baseline `0.7917`
  - `avg_input_tokens = 1098.75`
  - `avg_total_tokens = 1164.75`
  - `avg_output_tokens = 66`
  - `avg_elapsed_ms = 2980.65` vs baseline `6095.24`
- comparison:
  - aggregate total-token savings vs baseline: `12.74%`
  - aggregate latency savings vs baseline: `51.10%`

Interpretation:

- Claude also benefits materially from compiled shared context in the cold-start regime
- the winning stack is:
  - focused compiled context
  - `gemini-transfer` on debug/review/refactor
  - `capsule-mini72` on architecture
- this makes compiled shared context a cross-provider runtime lever, not a Gemini-specific feature

Interpretation:

- Flint is no longer OpenAI-only; the transport/runtime generalizes across providers
- the value is provider-specific:
  - OpenAI strong
  - Anthropic positive when routing is allowed to be selective
  - Gemini currently benefits from selective routing, but not enough to beat the terse baseline yet
- on `gpt-5.4`, a selective efficiency router collapses back to the same full-Flint routing, which is a good sign rather than a failure
- this validates the architecture decision to calibrate per model/provider instead of chasing one universal prompt
- it also validates the stronger claim that Flint is a policy layer, not just a compact notation

### Cache viability on current micro benchmarks

Runs checked:

- `evals/runs/gpt_5_4_mini_selective_efficiency.jsonl`
- `evals/runs/claude_sonnet_4_20250514_selective_efficiency.jsonl`
- `evals/runs/gemini_2_5_flash_selective_efficiency.jsonl`

Observed with `evals/cache_report.py`:

- `gpt-5.4-mini`: average input `124` to `154.75` tokens against a `1024`-token caching floor
- `claude-sonnet-4-20250514`: average input `147.25` to `173.75` tokens against a `1024`-token caching floor
- `gemini-2.5-flash`: average input `133.5` to `144.75` tokens against a `1024`-token caching floor
- all current variants report `verdict = too_small_for_cache`

Interpretation:

- prompt/context caching is not broken in the current setup
- it is simply irrelevant for the micro benchmark because the contracts are too short
- caching may matter later for larger tasks, longer codebase prompts, or persistent project prefixes, but it is not the lever that explains current wins

### Transient-provider robustness

Observed:

- Gemini calibration initially failed on a `503 UNAVAILABLE` spike
- the parser also exposed a real runtime bug where a long single-line text could be misread as a filesystem path

Changes made:

- retry/backoff was added to `run_openai.py`, `run_anthropic.py`, and `run_gemini.py`
- the parser now guards long single-line text instead of probing the filesystem blindly

Interpretation:

- benchmark reliability is part of the product, not just convenience
- provider noise and runtime hardening matter if Flint is meant to be a real transport layer rather than a lab demo

### `hybrid` mode, schema-first transport

Run:

- task file: `evals/tasks_hybrid.jsonl`
- transport: `schema-hybrid`
- prompt: `prompts/hybrid_schema.txt`
- schema: `schemas/hybrid_schema.json`
- model: `gpt-4o-mini`

Observed:

- `parse_rate = 1.0`
- `mode_match_rate = 1.0`
- `avg_output_tokens = 138`
- `avg_reasoning_tokens = 0`

Interpretation:

- schema-constrained transport can push raw parseability to `1.0`
- this is currently the strongest reliability result in the repo
- semantic quality still needs work, because a generic hybrid schema can overcompress task-specific details

### `hybrid` mode, micro-schema transport

Run:

- task files: `evals/tasks_debug.jsonl`, `evals/tasks_architecture.jsonl`, `evals/tasks_review.jsonl`, `evals/tasks_refactor.jsonl`
- transport: `schema-debug_hybrid`, `schema-architecture_hybrid`, `schema-review_hybrid`, `schema-refactor_hybrid`
- prompts: category-specific schema prompts
- model: `gpt-4o-mini`

Observed:

- raw `parse_rate = 1.0`
- raw `mode_match_rate = 1.0`
- `avg_reasoning_tokens = 0`
- output tokens stayed compact across categories

Interpretation:

- task-specific transport is the most credible route so far
- generic schema-first solved syntax, but micro-schemas solve syntax with less semantic flattening
- the next bottleneck is literal retention and higher-fidelity field design, not parseability

### `hybrid` mode, compact wire transport

Run:

- task files: `evals/tasks_debug.jsonl`, `evals/tasks_review.jsonl`, `evals/tasks_architecture.jsonl`, `evals/tasks_refactor.jsonl`
- transport: `schema-debug_wire`, `schema-review_wire`, `schema-architecture_wire`, `schema-refactor_wire`
- prompts: category-specific wire prompts
- model: `gpt-4o-mini`

Observed:

- debug: `87` output tokens vs `115` for direct schema, `parse_rate = 1.0`, better `must_include_rate`
- review: `79` output tokens vs `119` for direct schema, `parse_rate = 1.0`
- architecture: gains were fragile; once the schema was tightened to stop malformed decisions, the wire advantage mostly disappeared
- refactor: wire transport did not beat the direct schema lane

Interpretation:

- compact wire transport is promising, but not universally better
- the strongest current use cases are debugging and security review
- architecture and refactor currently prefer the more descriptive direct schema lane

### `hybrid` mode, lite wire transport with local canonicalization

Run:

- task files: `evals/tasks_debug.jsonl`, `evals/tasks_review.jsonl`
- transport: `schema-debug_wire_lite`, `schema-review_wire_lite`
- prompts: `prompts/debug_wire_lite.txt`, `prompts/review_wire_lite.txt`
- runtime: local canonicalization before render

Observed:

- debug: `64` output tokens, `505` effective total tokens, `parse_rate = 1.0`
- review: `73` output tokens, `376` effective total tokens, `parse_rate = 1.0`
- both beat the heavier wire schema on output tokens and effective total tokens

Interpretation:

- a lighter schema can work if the runtime performs a local canonicalization pass before rendering Flint
- this is currently the strongest answer to the input-overhead problem on categories where the wire lane already works
- the key insight is compiler-like: relax the transport contract slightly, then recover structure in a deterministic local pass

### `hybrid` mode, lite wire transport beyond debug and review

Run:

- task files: `evals/tasks_architecture.jsonl`, `evals/tasks_refactor.jsonl`
- transport: `schema-architecture_wire_lite`, `schema-refactor_wire_lite`
- prompts: `prompts/architecture_wire_lite.txt`, `prompts/refactor_wire_lite.txt`
- model: `gpt-4o-mini`

Observed:

- architecture wire-lite: `103` output tokens, `381` effective total tokens, `parse_rate = 1.0`, but `must_include_rate = 0.3333`
- refactor wire-lite: `69` output tokens, `453` effective total tokens, `parse_rate = 1.0`, but `must_include_rate = 0.5`

Interpretation:

- lite wire generalizes mechanically across categories
- but architecture and refactor expose the main semantic wall: very compact transport can overcompress the task signal even when syntax stays perfect
- this is why routing must remain category-aware and objective-aware

### Capsule v2 compiler

Run:

- task compiler: `src/flint/task_capsule.py`
- generated task files: `evals/tasks_*_capsule.jsonl`
- model: `gpt-4o-mini`

Observed:

- debug wire-lite capsule v2: `parse_rate = 1.0`, `must_include_rate = 1.0`, `exact_literal_rate = 1.0`, `526` effective total tokens
- review wire-lite capsule v2: `parse_rate = 1.0`, `exact_literal_rate = 1.0`, `399` effective total tokens
- architecture wire-lite capsule: `76` output tokens, `422` effective total tokens, but `must_include_rate = 0.3333`
- refactor wire-capsule v2: `114` output tokens, `558` effective total tokens, `must_include_rate = 0.75`, `exact_literal_rate = 1.0`

Interpretation:

- the local task compiler is now doing useful work
- `anchors:` plus structured fact extraction materially help literal retention and some task families
- the gain is uneven: debug improves sharply, architecture still loses semantic fidelity when overcompressed

### Packed transport experiment

Observed:

- top-level array schemas were rejected by the provider
- nested packed tuples inside a minimal object were also rejected due unsupported array-schema features

Interpretation:

- packed tuple transport is still interesting conceptually
- but the current provider contract makes that path impractical right now
- the better near-term path is lite object schemas plus local canonicalization

### Routed transport policy

Run:

- task file: `evals/tasks_hybrid.jsonl`
- policy: `profiles/micro_router_v1.json`
- composed run: `evals/runs/hybrid_routed_v1.jsonl`

Observed:

- `parse_rate = 1.0`
- `mode_match_rate = 1.0`
- `must_include_rate = 0.8125`
- `exact_literal_rate = 0.7917`
- `avg_output_tokens = 106` vs baseline terse `235`
- output token savings vs baseline: about `45.84%`
- `avg_total_tokens = 575.5` vs baseline `424`
- still much better than monolithic prompt-only Flint on the same task set (`886.75`)

Interpretation:

- the first credible Flint architecture is now a router, not a single prompt
- mixed transport beats one-size-fits-all transport
- the output-side win is large, but input overhead is still the main remaining economic problem

### Auto-suggested routing profiles

Run:

- script: `evals/suggest_profile.py`
- objectives: `quality`, `efficiency`
- outputs: `profiles/auto_quality_router_v1.json`, `profiles/auto_efficiency_router_v1.json`

Observed:

- the efficiency profile selected `debug_wire_lite`, `architecture_wire`, `review_wire_lite`, `refactor`
- composed run reached `97.75` average output tokens and `515.25` effective total tokens
- that is better on cost than the manual routed profile, but with weaker quality retention

Interpretation:

- profile selection should be objective-aware
- there is no single “best” router without deciding how much quality to trade for cost and latency
- the router should be treated as a learned policy artifact, not a hard-coded repo constant

### Routed policy, v3 profiles

Run:

- profiles: `profiles/auto_efficiency_router_v3.json`, `profiles/auto_quality_router_v3.json`, `profiles/auto_balanced_router_v1.json`
- composed runs: `evals/runs/hybrid_auto_efficiency_v3.jsonl`, `evals/runs/hybrid_auto_quality_v3.jsonl`, `evals/runs/hybrid_auto_balanced_v1.jsonl`
- model: `gpt-4o-mini`

Observed:

- efficiency v3:
  - `parse_rate = 1.0`
  - `avg_output_tokens = 70.5`
  - output savings vs baseline terse: `64.86%`
  - `avg_effective_total_tokens = 439`
  - total cost vs baseline terse: `+10.26%`
  - `must_include_rate = 0.4583`
  - `exact_literal_rate = 0.6667`
- balanced v1:
  - `parse_rate = 1.0`
  - `avg_output_tokens = 97.75`
  - output savings vs baseline terse: `51.61%`
  - `avg_effective_total_tokens = 476.25`
  - total cost vs baseline terse: `+19.79%`
  - `must_include_rate = 0.6458`
  - `exact_literal_rate = 1.0`
- quality v3:
  - `parse_rate = 1.0`
  - `avg_output_tokens = 115.75`
  - output savings vs baseline terse: `42.61%`
  - `avg_effective_total_tokens = 514.5`
  - total cost vs baseline terse: `+31.67%`
  - `must_include_rate = 0.8125`
  - `exact_literal_rate = 0.9167`

Interpretation:

- this is the clearest current frontier in the repo
- Flint now has a real Pareto surface:
  - efficiency-first gets very close to baseline total cost while crushing visible output size
  - balanced matches baseline `must_include_rate` while pushing `exact_literal_rate` to `1.0`
  - quality-first gives the best semantic retention, but still pays a clear input-cost premium
- the remaining wall is no longer parseability; it is input-side economics versus semantic retention

### Prompt-cache experiment

Run:

- repeated wire-format runs on `debug` and `review`
- used `--prompt-cache-key` and `--prompt-cache-retention 24h`

Observed:

- `cached_tokens = 0` in the current setup

Interpretation:

- prompt caching is still strategically important
- but in the current repo setup and provider behavior, it is not yet showing measurable benefit
- treat cache-aware cost reduction as an open engineering question, not a solved result

### Model transfer: `gpt-5.4-mini`

Run:

- baseline: `evals/runs/gpt54mini_baseline_hybrid_v1.jsonl`
- routed runs: `evals/runs/gpt54mini_hybrid_efficiency_v2.jsonl`, `evals/runs/gpt54mini_hybrid_balanced_v2.jsonl`
- prompts: tightened `wire_lite` prompts plus local audit expansion

Observed:

- first transfer from `gpt-4o-mini` prompts was bad: the terse baseline shrank to `131` output tokens on average while Flint became too verbose
- after tightening the `wire_lite` schema and prompt, and moving semantic recovery into the local audit renderer:
  - efficiency router: `parse_rate = 1.0`
  - `must_include_rate = 0.9375`
  - `exact_literal_rate = 1.0`
  - `avg_output_tokens = 101.25` vs baseline `131`
  - output savings vs baseline: `22.36%`
  - `avg_effective_total_tokens = 558.5` vs baseline `320`
  - total cost vs baseline: `+79.41%`
  - latency vs baseline: `-23.15%`

Interpretation:

- model transfer is not automatic
- stronger models compress their own terse baseline better, so Flint must become more typed and more bounded to stay competitive
- once the transport is tightened, Flint can beat the baseline on output size, latency, and retention simultaneously
- but the input-cost wall remains dominant on `gpt-5.4-mini`

### Model transfer: `gpt-5.4`

Run:

- baseline: `evals/runs/gpt54_baseline_hybrid_v1.jsonl`
- routed run: `evals/runs/gpt54_hybrid_efficiency_v1.jsonl`
- profile: mini-derived efficiency router with the tightened `wire_lite` lanes

Observed:

- `parse_rate = 1.0`
- `must_include_rate = 1.0`
- `exact_literal_rate = 1.0`
- `avg_output_tokens = 114` vs baseline `236.25`
- output savings vs baseline: `49.22%`
- `avg_effective_total_tokens = 571.25` vs baseline `425.25`
- total cost vs baseline: `+39.73%`
- latency vs baseline: `-33.98%`

Interpretation:

- the stronger model helps a lot
- with `gpt-5.4`, Flint now wins clearly on visible output compression, latency, and task-retention quality
- the remaining failure mode is narrow and concrete: uncached input overhead still prevents a total-token win

### Compiler-first micro capsules: `gpt-5.4-mini`

Run:

- task compiler: `python3 evals/build_task_capsules.py evals/tasks_hybrid.jsonl evals/tasks_hybrid_micro.jsonl --style micro`
- profile: `profiles/gpt54mini_micro_efficiency_router_v2.json`
- composed run: `evals/runs/gpt54mini_hybrid_micro_efficiency_v2.jsonl`
- baseline: `evals/runs/gpt54mini_baseline_hybrid_micro_v1.jsonl`

Observed:

- `parse_rate = 1.0`
- `must_include_rate = 1.0`
- `exact_literal_rate = 1.0`
- `avg_output_tokens = 84.25` vs baseline `128.75`
- output savings vs compiled baseline: `32.95%`
- `avg_effective_total_tokens = 358` vs baseline `252.75`
- total cost vs compiled baseline: `+44.31%`

Interpretation:

- compiler-first direct Flint is now syntactically stable on `gpt-5.4-mini`
- it wins strongly on visible output size
- but it still loses on total cost once the baseline also benefits from the same local task compiler
- this is the clearest current wall on smaller strong models

### Prompt-compressed direct Flint: `gpt-5.4-mini`

Run:

- prompts: `prompts/*_direct_sigil_compact.txt`
- profile: `profiles/gpt54mini_compact_efficiency_router_v1.json`
- composed run: `evals/runs/gpt54mini_hybrid_micro_compact_efficiency_v1.jsonl`
- baseline: `evals/runs/gpt54mini_baseline_hybrid_micro_v1.jsonl`

Observed:

- `parse_rate = 1.0`
- `must_include_rate = 0.9375`
- `exact_literal_rate = 1.0`
- `avg_input_tokens = 173.5` vs `273.75` in the earlier micro/direct setup
- `avg_output_tokens = 88.5` vs baseline `128.75`
- `avg_effective_total_tokens = 262` vs baseline `252.75`
- output savings vs compiled baseline: `29.47%`
- total cost vs compiled baseline: `+4.49%`
- latency savings vs compiled baseline: `18.25%`

Interpretation:

- this moved the mini-model wall from “far away” to “barely above parity”
- the direct prompt contract is now the main remaining bottleneck
- the system is entering a narrow optimum:
  - too much prompt structure raises input overhead
  - too little structure collapses parseability

### Overcompression failure band

Runs:

- `prompts/*_direct_sigil_lean.txt`
- `prompts/*_direct_sigil_tight.txt`
- `prompts/*_direct_sigil_compact_v3.txt`
- `max-output-tokens = 90` experiment on compact prompts

Observed:

- lean prompts reduced cost sharply but often collapsed into non-Flint bullets or headings
- tight prompts overfit on some categories and regressed parseability or mode match
- `compact v3` and `cap90` crossed the same boundary from a different angle: cheaper contracts, but unstable formal outputs

Interpretation:

- there is now evidence for a real stability frontier on `gpt-5.4-mini`
- prompt compression still helps, but only within a narrow band
- further gains on the mini model probably require:
  - better provider-side grammar control
  - cache reuse that actually materializes
  - or a stronger local compiler/repair stage

### Compiler-first micro capsules: `gpt-5.4`

Run:

- task compiler: `python3 evals/build_task_capsules.py evals/tasks_hybrid.jsonl evals/tasks_hybrid_micro.jsonl --style micro`
- profile: `profiles/gpt54_micro_efficiency_router_v3.json`
- composed run: `evals/runs/gpt54_hybrid_micro_efficiency_v3.jsonl`
- baseline: original terse run `evals/runs/gpt54_baseline_hybrid_v1.jsonl`

Observed:

- `parse_rate = 1.0`
- `must_include_rate = 1.0`
- `exact_literal_rate = 1.0`
- `avg_output_tokens = 84.5` vs baseline `236.25`
- output savings vs baseline: `62.63%`
- `avg_effective_total_tokens = 327` vs baseline `425.25`
- total cost savings vs baseline: `18.72%`
- latency savings vs baseline: `59.68%`

Interpretation:

- this is the first real end-to-end breakthrough in the repo
- the winning recipe is:
  - local task compiler
  - direct Flint surface form
  - local repair plus audit materialization
  - strong model (`gpt-5.4`)
- the claim is still narrow:
  - it beats the original natural-language terse baseline
  - it does not yet beat an already-compiled terse baseline on `gpt-5.4-mini`

### Direct Flint repair lane

Observed:

- `materialize_direct_sigil()` now repairs missing audit blocks, header drift like `@sigil_v0_hybrid`, unicode operator drift, and some compact-expression whitespace drift
- direct category prompts were tightened around small fixed atom sets
- the repair path is covered by regression tests

Interpretation:

- direct Flint no longer needs to be treated as a toy freeform lane
- it is now a realistic low-overhead transport candidate
- the important lesson is architectural: the cheapest lane became viable only after moving more work into deterministic local repair

### Local re-rendering

New utility:

- script: `evals/rerender_run.py`

Purpose:

- re-materialize structured run rows with the current local renderer without re-spending API calls

Interpretation:

- this matters because more of Flint's semantic recovery now lives in deterministic local rendering
- it also makes iteration faster: prompt changes require new API calls, renderer changes do not

### `draft2schema` transport

Run:

- task files: `evals/tasks_debug.jsonl`, `evals/tasks_architecture.jsonl`
- transport: `draft2schema-debug_hybrid`, `draft2schema-architecture_hybrid`
- draft prompt: `prompts/hybrid_strict.txt`
- final prompt: category-specific schema prompt
- model: `gpt-4o-mini`

Observed:

- raw `parse_rate = 1.0`
- raw `mode_match_rate = 1.0`
- `avg_stage_count = 2`
- end-to-end `total_tokens` and `elapsed_ms` increased sharply
- no quality win on the measured tasks

Interpretation:

- the two-stage transport is now implemented and benchmarkable
- on the current task set and prompt design, it is not worth the extra stage
- this is a useful negative result: draft conditioning should be treated as a selective fallback, not the default Flint lane

### Literal-aware schema correction

Change:

- schema regexes now allow quoted literal arguments like `timeline("4 months")`
- category prompts now explicitly forbid normalizing critical literals away

Observed:

- architecture exact-literal retention improved from `0.3333` to `0.6667`
- architecture must-include retention improved to `1.0`
- raw parseability stayed at `1.0`

Interpretation:

- some semantic loss was caused by the transport grammar itself, not only by prompt quality
- compact IRs still need a literal-preservation escape hatch

### `compile` mode

Run:

- task file: `evals/tasks_compile.jsonl`
- prompt: `prompts/compile_strict.txt`
- model: `gpt-5.2`
- reasoning effort: `none`

Observed:

- `avg_output_tokens = 216`
- `avg_reasoning_tokens = 0`
- `parse_rate = 0.0`

Interpretation:

- compile mode is still too permissive
- the model drifts back toward compressed prose instead of staying inside the IR

### `compile` mode, strict v2

Run:

- task file: `evals/tasks_compile.jsonl`
- prompt: `prompts/compile_strict.txt`
- model: `gpt-5.2`
- reasoning effort: `none`

Observed:

- `parse_rate = 1.0`
- `mode_match_rate = 1.0`
- `avg_output_tokens = 137`
- `avg_reasoning_tokens = 0`

Interpretation:

- compile mode became stable after switching from “symbolic but permissive” to a tighter typed template
- this supports the main Flint hypothesis: the gain comes from a compact IR plus strict production rules, not from freeform symbolic style

## Main Lessons

1. Underspecified prompts destroy benchmark validity. The model asks for more context instead of solving the task.
2. Mixed-mode evaluation is too noisy at the start. Benchmark each mode separately.
3. Parseability depends more on hard syntax constraints than on generic “be symbolic” instructions.
4. Reasoning-effort `none` is a useful pressure test for Flint because it isolates representation discipline from hidden thinking budgets.

## Next Technical Targets

1. Raise `compile` parse rate to at least `0.9`.
2. Expand `hybrid` smoke tests from one task to the full hybrid task set.
3. Add quality checks beyond keyword retention, especially for patch correctness and risk localization.
4. Route `draft2schema` only when the cheaper direct schema lane shows low confidence or poor literal retention.
5. Keep tightening micro-schemas so exact literals survive without inflating output tokens too much.
6. Reduce direct-prompt overhead further, because compiler-first Flint still loses to a compiled terse baseline on `gpt-5.4-mini`.
7. Learn better category policies from larger eval sets so the auto-router is less noisy and less sample-sensitive.
8. Test whether cache-aware prefix reuse or provider-side grammar constraints can close the remaining mini-model gap.
