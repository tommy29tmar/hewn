# Hewn vs Verbose Claude vs Caveman — benchmark report

## TL;DR — what this report actually shows

This is an honest, mixed picture. Hewn does NOT dominate Caveman on
every axis. Read the numbers, not the marketing.

**Where Hewn wins:**
- **Multi-turn (T4)**: Hewn's classifier hook saves **~5,000 cumulative
  output tokens per 5-turn sequence** vs the same Hewn prompt without
  the hook. That is the hook's whole reason to exist; it works.
  - On `debug-prod-incident` (5 turns): hewn_full **1,301 tokens** vs
    caveman_full 1,612 vs baseline 5,550. Concept coverage 100% vs 98%
    (caveman) vs 100% (baseline).
  - On `design-feature` (5 turns): hewn_full 5,295 vs caveman_full
    6,840 vs baseline 8,841.
- **Long-context with compact technical tasks (T3
  `rate-limit-xff-review`)**: prompt is in IR-like shape (`anchors:`,
  `diff:`, `deliver:`). baseline / terse / caveman_full ALL replied
  "no task specified, what do you want?" (concepts 0/6). hewn_full
  produced detailed multi-finding security review (concepts 6/6, 4/6,
  2/6 across 3 runs; literals 2/2 preserved). Cost: Hewn used 4–6k
  tokens vs caveman ~70 — but they returned different things (Hewn:
  the actual review; Caveman: a clarifying question).
- **Literal preservation (T1b)**: Hewn 100% vs Caveman 93%.

**Where Caveman wins:**
- **Raw token compression on standard short Q&A (T1a/T1b)**: confirms
  Caveman's published claim. On the 10 prompts vendored from their
  `evals/prompts/en.txt`, caveman_full uses **59% fewer tokens than
  terse** (median), 60% fewer than baseline. Hewn produces ~60% MORE
  tokens than caveman on these prompts (hewn_full 264 mean tokens vs
  caveman_full 167).

**Where everyone loses:**
- **Readability for non-technical users (T2)**: every compression arm
  hurts comprehension for novices vs plain Claude. Persona-judge "non-
  tech readability" mean ratio: baseline **78%** > hewn_prompt_only
  60% > terse 43% > hewn_full 35% > caveman_full_plus_ultra 28% >
  caveman_full **20%**. The more the system prompt pushes terseness,
  the harder the answer is for a beginner. Don't use compression modes
  if your users are not technical.
- **Polished-prose tasks (T5)**: every arm partially refused or gave a
  near-empty stub on the "Smart Drafts release note" task (10–68
  tokens), suggesting the model needs more concrete context for
  marketing-style prose regardless of system prompt. The outage
  apology was handled similarly across all arms (~480 tokens). Hewn
  does not improve here.

**Methodology honesty (read the full report for details):**
- T1a is a **strict replication** of Caveman's `evals/llm_run.py` (1
  run, 3 arms, tiktoken o200k_base). T1b–T5 are Hewn extensions.
- T0 calibrates the **append-vs-replace exposure asymmetry** between
  Hewn arms (`--append-system-prompt` → inherits CLAUDE.md + Claude
  Code default) and Caveman arms (`--system-prompt` → replaces). The
  calibration shows the bias is small for terse (~+7 tokens median)
  but +52 tokens for caveman → Hewn-vs-Caveman is observed under
  asymmetric exposure and may be inflated for Hewn by ~50 tokens/call.
- We use the same model, same CLI, same prompts as Caveman. We pin
  Caveman SKILL.md by sha256 (vendored under `caveman_source/`).
- Raw `claude -p` JSON snapshots committed under
  `benchmarks/snapshots/raw/` so any number can be re-derived.

---

_Generated: 2026-04-22T00:56:33.572071+00:00_
_Model: `claude-opus-4-7`_
_Claude CLI: 2.1.117 (Claude Code)_
_Hewn repo commit: dd864d7db31fde7d200f72818e1ac6aea8497d95_
_Caveman repo commit pinned: 84cc3c14fa1e10182adaced856e003406ccd250d_
_Caveman SKILL.md sha256: `1762eb9ab0b566d70f51b040dbfd77d1f5be89cfa70da874564bda38c111be7c`_
_Random seed: `hewn-bench-v1`_
_Environment: NOT isolated (option B). User CLAUDE.md hash: `fed963e9ef7e` (169 words)._

## What this report measures

Six arms tested via `claude -p` / `hewn -p` (OAuth subscription, no
direct API key billing):

| Arm | Mechanism |
|---|---|
| `baseline` | `claude -p`, no system prompt |
| `terse` | `claude -p --system-prompt "Answer concisely."` |
| `caveman_full` | `claude -p --system-prompt "Answer concisely.\n\n" + caveman SKILL.md` (vendored from caveman repo) |
| `caveman_full_plus_ultra_directive` | `caveman_full` + appended "Default intensity: ultra…" — **NOT** Caveman's official Ultra (needs skill runtime); our directive-based variant |
| `hewn_prompt_only` | `claude -p --append-system-prompt <hewn prompt>` (no hook) |
| `hewn_full` | `hewn -p` real wrapper (prompt + classifier hook) |

Tracks:

- **T0** — append-vs-replace exposure calibration (10 prompts × 1 run × 4 arms)
- **T1a** — strict Caveman parity, replicates their `evals/llm_run.py` (10 prompts × 1 run × 3 arms)
- **T1b** — extended on Caveman's own prompts (10 × 3 × 6)
- **T2** — vibe / non-tech user prompts (5 × 3 × 6)
- **T3** — long context (~5k handbook + task) (3 × 3 × 6)
- **T4** — multi-turn 5-turn sequences (2 × 2 × 5)
- **T5** — expansive prose (honesty: where Hewn should NOT win) (2 × 2 × 6)

## Honesty box

- **Caveman parity** label applies ONLY to T1a (1 run, 3 arms, tiktoken,
  matches `evals/llm_run.py`).
- **Hewn-vs-baseline** is causal: both arms inherit Claude Code's default
  system prompt + user CLAUDE.md.
- **Hewn-vs-Caveman/terse** is **observational under asymmetric
  exposure**: `--system-prompt` replaces, `--append-system-prompt` adds.
  T0 calibrates the magnitude on `short_en`; T2-T5 reported as raw
  observational only (no per-prompt calibration).
- `caveman_full_plus_ultra_directive` is OUR directive-based variant,
  NOT Caveman's official Ultra (which is invoked via `/caveman ultra`
  through the skill runtime, unavailable in `--system-prompt` mode).
- All raw `claude -p` JSON snapshots committed under
  `benchmarks/snapshots/raw/` for deterministic re-derivation.
- Hewn classifier hook is local Python (no extra API call), but DOES
  inject `additionalContext` → measured as `cache_creation_input_tokens`
  delta, NOT `input_tokens` delta (verified empirically).


## T1a — Strict Caveman parity

Replicates Caveman `evals/llm_run.py` methodology precisely: `claude -p --system-prompt <x>`, **1 run per arm**, 10 prompts vendored verbatim from caveman repo, output tokens via tiktoken `o200k_base` (matches Caveman's `evals/measure.py`).

**Honest delta** per Caveman's own README: skill vs `__terse__`, NOT skill vs baseline.

| Prompt | baseline | terse | caveman_full | savings vs terse |
|---|---:|---:|---:|---:|
| `cors-errors` | 306 | 336 | 129 | 62% |
| `debounce-search` | 127 | 137 | 32 | 77% |
| `explain-db-pool` | 429 | 394 | 96 | 76% |
| `fix-node-memory-leak` | 319 | 307 | 223 | 27% |
| `git-rebase-vs-merge` | 191 | 131 | 49 | 63% |
| `hash-table-collisions` | 332 | 267 | 83 | 69% |
| `queue-vs-topic` | 141 | 162 | 60 | 63% |
| `react-rerender-parent` | 181 | 149 | 84 | 44% |
| `sql-explain` | 253 | 299 | 114 | 62% |
| `tcp-vs-udp` | 98 | 136 | 73 | 46% |
| **median** | | | | **62%** |
| **mean** | | | | **59%** |
| **range** | | | | **27% – 77%** |
| **stdev** | | | | **15%** |

Totals: baseline 2377 / terse 2318 (`2%` vs baseline) / caveman_full 943 (`59%` vs terse, `60%` vs baseline).

## T0 — Append-vs-replace exposure calibration

Measures the output-token delta between `--system-prompt` (replace) and `--append-system-prompt` (add to default + CLAUDE.md). Positive delta = appending makes output **longer**. Negative = appending compresses **more**.

Both arms use the same content (`Answer concisely.` for terse, same + Caveman SKILL.md for caveman_full). Only the flag differs.

| Prompt | terse (replace) | terse (append) | Δ tokens | caveman (replace) | caveman (append) | Δ tokens |
|---|---:|---:|---:|---:|---:|---:|
| `cors-errors` | 532 | 500 | -32 | 204 | 191 | -13 |
| `debounce-search` | 245 | 255 | +10 | 62 | 178 | +116 |
| `explain-db-pool` | 529 | 546 | +17 | 217 | 208 | -9 |
| `fix-node-memory-leak` | 469 | 587 | +118 | 410 | 492 | +82 |
| `git-rebase-vs-merge` | 263 | 150 | -113 | 73 | 169 | +96 |
| `hash-table-collisions` | 331 | 315 | -16 | 181 | 228 | +47 |
| `queue-vs-topic` | 235 | 262 | +27 | 124 | 182 | +58 |
| `react-rerender-parent` | 388 | 356 | -32 | 209 | 176 | -33 |
| `sql-explain` | 421 | 523 | +102 | 236 | 230 | -6 |
| `tcp-vs-udp` | 175 | 172 | -3 | 134 | 242 | +108 |
| **median** | | | **+3** | | | **+52** |
| **mean** | | | **+7** | | | **+44** |

_Interpretation: a positive median delta means stock Caveman/terse (replace) numbers underestimate compression vs. Hewn arms (append); observed Hewn-vs-Caveman savings on T1b/T2-T5 are inflated by approximately this magnitude._

## T1b — Extended short_en (Hewn extension)

All 6 arms × 3 runs × 10 prompts. Median across runs per (arm, prompt). Output tokens from Anthropic `usage.output_tokens` (ground truth, not tiktoken approximation).

Cell values: median(output_tokens). `hewn_full` includes the classifier hook overhead (extra `cache_creation_input_tokens`, see appendix).

### Output tokens per prompt × arm

| Prompt | baseline | terse | caveman_full | caveman+ultra | hewn_prompt_only | hewn_full |
|---|---:|---:|---:|---:|---:|---:|
| `cors-errors` | 423 | 432 | 248 | 219 | 385 | 333 |
| `debounce-search` | 225 | 212 | 61 | 53 | 212 | 159 |
| `explain-db-pool` | 661 | 583 | 98 | 62 | 566 | 358 |
| `fix-node-memory-leak` | 701 | 594 | 442 | 319 | 647 | 374 |
| `git-rebase-vs-merge` | 218 | 248 | 103 | 102 | 225 | 158 |
| `hash-table-collisions` | 309 | 324 | 145 | 178 | 329 | 341 |
| `queue-vs-topic` | 190 | 191 | 128 | 122 | 226 | 277 |
| `react-rerender-parent` | 315 | 388 | 140 | 131 | 357 | 214 |
| `sql-explain` | 266 | 414 | 178 | 118 | 391 | 255 |
| `tcp-vs-udp` | 181 | 171 | 125 | 95 | 180 | 173 |
| **mean** | **349** | **356** | **167** | **140** | **352** | **264** |

### Hewn-vs-comparator savings — `(appended, observed)` pair

Cross-track join: `appended` side from T0 single run; `observed` side and `hewn_full` from T1b median-of-3-runs.

**vs Caveman full** — savings = `comparator − hewn_full` tokens; positive = Hewn fewer tokens.

| Prompt | observed (T1b stock) | appended (T0 calibrated) |
|---|---:|---:|
| `cors-errors` | -85 | -142 |
| `debounce-search` | -98 | +19 |
| `explain-db-pool` | -260 | -150 |
| `fix-node-memory-leak` | +68 | +118 |
| `git-rebase-vs-merge` | -55 | +11 |
| `hash-table-collisions` | -196 | -113 |
| `queue-vs-topic` | -149 | -95 |
| `react-rerender-parent` | -74 | -38 |
| `sql-explain` | -77 | -25 |
| `tcp-vs-udp` | -48 | +69 |
| **median** | **-81** | **-31** |
| **mean** | **-97** | **-34** |

**vs terse** — same shape:

| Prompt | observed (T1b stock) | appended (T0 calibrated) |
|---|---:|---:|
| `cors-errors` | +99 | +167 |
| `debounce-search` | +53 | +96 |
| `explain-db-pool` | +225 | +188 |
| `fix-node-memory-leak` | +220 | +213 |
| `git-rebase-vs-merge` | +90 | -8 |
| `hash-table-collisions` | -17 | -26 |
| `queue-vs-topic` | -86 | -15 |
| `react-rerender-parent` | +174 | +142 |
| `sql-explain` | +159 | +268 |
| `tcp-vs-udp` | -2 | -1 |
| **median** | **+94** | **+119** |
| **mean** | **+91** | **+102** |

### Hewn-vs-baseline (causal — both arms inherit default+CLAUDE.md)

| Prompt | baseline | hewn_full | savings |
|---|---:|---:|---:|
| `cors-errors` | 423 | 333 | 21% |
| `debounce-search` | 225 | 159 | 29% |
| `explain-db-pool` | 661 | 358 | 46% |
| `fix-node-memory-leak` | 701 | 374 | 47% |
| `git-rebase-vs-merge` | 218 | 158 | 28% |
| `hash-table-collisions` | 309 | 341 | −10% |
| `queue-vs-topic` | 190 | 277 | −46% |
| `react-rerender-parent` | 315 | 214 | 32% |
| `sql-explain` | 266 | 255 | 4% |
| `tcp-vs-udp` | 181 | 173 | 4% |
| **median** | | | **24%** |
| **mean** | | | **16%** |
| **range** | | | **−46% – 47%** |

### Stability (stdev of output_tokens across 3 runs per arm × prompt)

| Arm | mean stdev across prompts |
|---|---:|
| baseline | 54.7 |
| terse | 59.8 |
| caveman_full | 36.7 |
| caveman_full_plus_ultra_directive | 18.6 |
| hewn_prompt_only | 65.7 |
| hewn_full | 48.1 |

## T2 — Vibe / non-tech user prompts

3 runs × 5 prompts × 6 arms. Median across runs per (arm, prompt). Hewn-vs-Caveman/terse numbers are **observational under asymmetric exposure** (no T0-style appended-comparator calibration on these prompts).

### Output tokens per prompt × arm (median)

| Prompt | baseline | terse | caveman_full | caveman+ultra | hewn_prompt_only | hewn_full |
|---|---:|---:|---:|---:|---:|---:|
| `add-search-bar` | 197 | 117 | 266 | 199 | 176 | 76 |
| `login-button-broken` | 227 | 93 | 122 | 106 | 182 | 236 |
| `make-website-faster` | 43 | 94 | 59 | 131 | 89 | 72 |
| `spaghetti-code` | 442 | 422 | 427 | 451 | 440 | 310 |
| `typeerror-undefined-map` | 254 | 277 | 116 | 105 | 298 | 257 |
| **mean** | **233** | **201** | **198** | **198** | **237** | **190** |

### Hewn-vs-baseline (causal — both arms inherit default+CLAUDE.md)

| Prompt | baseline | hewn_full | savings |
|---|---:|---:|---:|
| `add-search-bar` | 197 | 76 | 61% |
| `login-button-broken` | 227 | 236 | −4% |
| `make-website-faster` | 43 | 72 | −67% |
| `spaghetti-code` | 442 | 310 | 30% |
| `typeerror-undefined-map` | 254 | 257 | −1% |
| **median** | | | **−1%** |
| **mean** | | | **4%** |

### Wall-clock latency (median, ms)

| Prompt | baseline | terse | caveman_full | caveman+ultra | hewn_prompt_only | hewn_full |
|---|---:|---:|---:|---:|---:|---:|
| `add-search-bar` | 5397 | 3948 | 6454 | 5872 | 4197 | 6060 |
| `login-button-broken` | 4985 | 3396 | 4849 | 4063 | 4193 | 5808 |
| `make-website-faster` | 2479 | 3412 | 4133 | 4344 | 3342 | 3727 |
| `spaghetti-code` | 10576 | 10273 | 10834 | 12322 | 10668 | 8929 |
| `typeerror-undefined-map` | 7046 | 5795 | 4021 | 4078 | 7166 | 6870 |

## T3 — Long context (~5k handbook prefix)

3 runs × 3 prompts × 6 arms. Median across runs per (arm, prompt). Hewn-vs-Caveman/terse numbers are **observational under asymmetric exposure** (no T0-style appended-comparator calibration on these prompts).

### Output tokens per prompt × arm (median)

| Prompt | baseline | terse | caveman_full | caveman+ultra | hewn_prompt_only | hewn_full |
|---|---:|---:|---:|---:|---:|---:|
| `body-size-rollout-plan` | 1712 | 1548 | 1389 | 1630 | 2158 | 1441 |
| `rate-limit-xff-review` | 146 | 100 | 72 | 54 | 252 | 5180 |
| `transfer-handler-review` | 772 | 801 | 532 | 560 | 1066 | 1193 |
| **mean** | **877** | **816** | **664** | **748** | **1159** | **2605** |

### Hewn-vs-baseline (causal — both arms inherit default+CLAUDE.md)

| Prompt | baseline | hewn_full | savings |
|---|---:|---:|---:|
| `body-size-rollout-plan` | 1712 | 1441 | 16% |
| `rate-limit-xff-review` | 146 | 5180 | −3448% |
| `transfer-handler-review` | 772 | 1193 | −55% |
| **median** | | | **−55%** |
| **mean** | | | **−1162%** |

### Wall-clock latency (median, ms)

| Prompt | baseline | terse | caveman_full | caveman+ultra | hewn_prompt_only | hewn_full |
|---|---:|---:|---:|---:|---:|---:|
| `body-size-rollout-plan` | 31892 | 26159 | 25480 | 30524 | 36315 | 31043 |
| `rate-limit-xff-review` | 4864 | 2556 | 2968 | 2645 | 5879 | 84026 |
| `transfer-handler-review` | 12623 | 13293 | 9240 | 9540 | 18778 | 22691 |

## T4 — Multi-turn (drift + isolated hook value)

Each (arm, sequence, run) replays 5 user turns via explicit `--resume <session_id>`. Cumulative output tokens summed across all 5 turns.

### Cumulative output tokens per sequence × arm (median across 2 runs)

| Sequence | baseline | terse | caveman_full | hewn_prompt_only | hewn_full |
|---|---:|---:|---:|---:|---:|
| `debug-prod-incident` | 5550 | 2255 | 1612 | 6030 | 1301 |
| `design-feature` | 8841 | 5585 | 6840 | 10902 | 5295 |

### Hook value — `(hewn_prompt_only − hewn_full)` cumulative deltas

Positive Δ output_tokens = hook makes hewn_full produce **fewer** tokens. Positive Δ cache_creation = hook injects extra `additionalContext` (expected; classifier injection is the hook's job).

| Sequence | Δ output_tokens (median) | Δ cache_creation_input (median) |
|---|---:|---:|
| `debug-prod-incident` | +4729 | +7088 |
| `design-feature` | +5607 | -1454 |

### Session-id isolation check

OK — no session_id collision across distinct (arm, seq, run) tuples.

## T5 — Expansive prose (honesty: Hewn should NOT win)

2 runs × 2 prompts × 6 arms. Median across runs per (arm, prompt). Hewn-vs-Caveman/terse numbers are **observational under asymmetric exposure** (no T0-style appended-comparator calibration on these prompts).

### Output tokens per prompt × arm (median)

| Prompt | baseline | terse | caveman_full | caveman+ultra | hewn_prompt_only | hewn_full |
|---|---:|---:|---:|---:|---:|---:|
| `outage-apology-email` | 481 | 483 | 538 | 450 | 503 | 460 |
| `smart-drafts-release-note` | 13 | 10 | 12 | 14 | 18 | 68 |
| **mean** | **247** | **247** | **275** | **232** | **261** | **264** |

### Hewn-vs-baseline (causal — both arms inherit default+CLAUDE.md)

| Prompt | baseline | hewn_full | savings |
|---|---:|---:|---:|
| `outage-apology-email` | 481 | 460 | 4% |
| `smart-drafts-release-note` | 13 | 68 | −404% |
| **median** | | | **−200%** |
| **mean** | | | **−200%** |

### Wall-clock latency (median, ms)

| Prompt | baseline | terse | caveman_full | caveman+ultra | hewn_prompt_only | hewn_full |
|---|---:|---:|---:|---:|---:|---:|
| `outage-apology-email` | 11520 | 10397 | 11910 | 11079 | 10463 | 10479 |
| `smart-drafts-release-note` | 1680 | 3024 | 1779 | 1629 | 2207 | 2711 |

## Quality — concepts coverage, literals, format compliance, judge failure rates

### T1a

| Arm | concepts covered (mean ratio) | literals preserved (mean) | IR valid (rate) | filler/100w (mean) | concept-judge failures | readability (mean true ratio) |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 95% | 100% | 0% | 0.1 | 0 | — |
| caveman_full | 91% | 100% | 0% | 0.0 | 0 | — |
| terse | 95% | 100% | 0% | 0.1 | 0 | — |

### T1b

| Arm | concepts covered (mean ratio) | literals preserved (mean) | IR valid (rate) | filler/100w (mean) | concept-judge failures | readability (mean true ratio) |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 96% | 93% | 0% | 0.2 | 0 | — |
| caveman_full | 95% | 93% | 0% | 0.0 | 0 | — |
| caveman_full_plus_ultra_directive | 93% | 80% | 0% | 0.1 | 0 | — |
| hewn_full | 96% | 100% | 10% | 0.2 | 0 | — |
| hewn_prompt_only | 96% | 93% | 0% | 0.2 | 0 | — |
| terse | 96% | 100% | 0% | 0.2 | 0 | — |

### T2

| Arm | concepts covered (mean ratio) | literals preserved (mean) | IR valid (rate) | filler/100w (mean) | concept-judge failures | readability (mean true ratio) |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 47% | 50% | 0% | 0.1 | 0 | 78% |
| caveman_full | 78% | 33% | 0% | 0.0 | 0 | 20% |
| caveman_full_plus_ultra_directive | 83% | 17% | 0% | 0.1 | 0 | 28% |
| hewn_full | 70% | 50% | 0% | 0.8 | 0 | 35% |
| hewn_prompt_only | 45% | 50% | 0% | 0.3 | 0 | 60% |
| terse | 65% | 50% | 0% | 0.4 | 0 | 43% |

### T3

| Arm | concepts covered (mean ratio) | literals preserved (mean) | IR valid (rate) | filler/100w (mean) | concept-judge failures | readability (mean true ratio) |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 5% | 0% | 0% | 0.5 | 0 | — |
| caveman_full | 5% | 0% | 0% | 0.0 | 0 | — |
| caveman_full_plus_ultra_directive | 5% | 0% | 0% | 0.0 | 0 | — |
| hewn_full | 27% | 42% | 0% | 0.1 | 0 | — |
| hewn_prompt_only | 5% | 0% | 0% | 0.0 | 0 | — |
| terse | 5% | 0% | 0% | 0.0 | 0 | — |

### T4

| Arm | concepts covered (mean ratio) | literals preserved (mean) | IR valid (rate) | filler/100w (mean) | concept-judge failures | readability (mean true ratio) |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 100% | — | 0% | 0.4 | 0 | — |
| caveman_full | 98% | — | 0% | 0.1 | 0 | — |
| hewn_full | 100% | — | 20% | 0.1 | 0 | — |
| hewn_prompt_only | 95% | — | 0% | 0.3 | 0 | — |
| terse | 95% | — | 0% | 0.3 | 0 | — |

### T5

| Arm | concepts covered (mean ratio) | literals preserved (mean) | IR valid (rate) | filler/100w (mean) | concept-judge failures | readability (mean true ratio) |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0% | 0% | 0% | 0.4 | 0 | — |
| caveman_full | 0% | 0% | 0% | 0.3 | 0 | — |
| caveman_full_plus_ultra_directive | 0% | 0% | 0% | 0.2 | 0 | — |
| hewn_full | 0% | 0% | 0% | 0.5 | 0 | — |
| hewn_prompt_only | 0% | 0% | 0% | 0.3 | 0 | — |
| terse | 0% | 0% | 0% | 0.4 | 0 | — |
