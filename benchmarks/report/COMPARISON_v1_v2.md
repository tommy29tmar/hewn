# Hewn v1 → v2 comparison

v1 = original 2026-04-22 run with the soft prose-caveman directive.
v2 = post-Codex tightening: stricter prose-caveman + new MICRO_PROSE mode + expanded IR routing for technical Q&A (see commit after `66c9d8d`).

Caveman/baseline/terse arms are UNCHANGED across versions and shown as reference. Differences in those columns reflect model nondeterminism only.

## T1b — hewn_full v1 → v2 vs unchanged comparators

| prompt | hewn_full v1 | hewn_full v2 | Δ tokens | Δ % | caveman_full (unchanged) | caveman_full_plus_ultra_directive (unchanged) | baseline (unchanged) |
|---|---|---|---|---|---|---|---|
| `cors-errors` | 333 | 59 | -274 | −82% | 248 | 219 | 423 |
| `debounce-search` | 159 | 59 | -100 | −63% | 61 | 53 | 225 |
| `explain-db-pool` | 358 | 56 | -302 | −84% | 98 | 62 | 661 |
| `fix-node-memory-leak` | 374 | 59 | -315 | −84% | 442 | 319 | 701 |
| `git-rebase-vs-merge` | 158 | 66 | -92 | −58% | 103 | 102 | 218 |
| `hash-table-collisions` | 341 | 62 | -279 | −82% | 145 | 178 | 309 |
| `queue-vs-topic` | 277 | 74 | -203 | −73% | 128 | 122 | 190 |
| `react-rerender-parent` | 214 | 51 | -163 | −76% | 140 | 131 | 315 |
| `sql-explain` | 255 | 59 | -196 | −77% | 178 | 118 | 266 |
| `tcp-vs-udp` | 173 | 70 | -103 | −60% | 125 | 95 | 181 |
| **mean** | **264** | **61** | **-202** | **−77%** | **166** | **139** | **348** |

## T2 — hewn_full v1 → v2 vs unchanged comparators

| prompt | hewn_full v1 | hewn_full v2 | Δ tokens | Δ % | caveman_full (unchanged) | caveman_full_plus_ultra_directive (unchanged) | baseline (unchanged) |
|---|---|---|---|---|---|---|---|
| `add-search-bar` | 76 | 42 | -34 | −45% | 266 | 199 | 197 |
| `login-button-broken` | 236 | 44 | -192 | −81% | 122 | 106 | 227 |
| `make-website-faster` | 72 | 43 | -29 | −40% | 59 | 131 | 43 |
| `spaghetti-code` | 310 | 55 | -255 | −82% | 427 | 451 | 442 |
| `typeerror-undefined-map` | 257 | 56 | -201 | −78% | 116 | 105 | 254 |
| **mean** | **190** | **48** | **-142** | **−75%** | **198** | **198** | **232** |

## T3 — hewn_full v1 → v2 vs unchanged comparators

| prompt | hewn_full v1 | hewn_full v2 | Δ tokens | Δ % | caveman_full (unchanged) | caveman_full_plus_ultra_directive (unchanged) | baseline (unchanged) |
|---|---|---|---|---|---|---|---|
| `body-size-rollout-plan` | 1441 | 1380 | -61 | −4% | 1389 | 1630 | 1712 |
| `rate-limit-xff-review` | 5180 | 242 | -4938 | −95% | 72 | 54 | 146 |
| `transfer-handler-review` | 1193 | 788 | -405 | −34% | 532 | 560 | 772 |
| **mean** | **2604** | **803** | **-1801** | **−69%** | **664** | **748** | **876** |

## T5 — hewn_full v1 → v2 vs unchanged comparators

| prompt | hewn_full v1 | hewn_full v2 | Δ tokens | Δ % | caveman_full (unchanged) | caveman_full_plus_ultra_directive (unchanged) | baseline (unchanged) |
|---|---|---|---|---|---|---|---|
| `smart-drafts-release-note` | 68 | 16 | -52 | −76% | 12 | 14 | 13 |
| `outage-apology-email` | 460 | 486 | +25 | +6% | 538 | 450 | 481 |
| **mean** | **264** | **251** | **-13** | **−5%** | **275** | **232** | **247** |

## T4 — multi-turn cumulative tokens v1 → v2

| sequence | hewn_full v1 (median) | hewn_full v2 (median) | Δ tokens | Δ % | caveman_full | baseline |
|---|---:|---:|---:|---:|---:|---:|
| `debug-prod-incident` | 1301 | 353 | -948 | −73% | 1612 | 5550 |
| `design-feature` | 5295 | 992 | -4302 | −81% | 6840 | 8841 |

## Quality side-by-side

### T1b concept coverage (mean ratio)

| arm | mean coverage | n |
|---|---:|---:|
| baseline | 96% | 30 |
| terse | 96% | 30 |
| caveman_full | 95% | 30 |
| caveman_full_plus_ultra_directive | 93% | 30 |
| hewn_full_v1 | 96% | 30 |
| hewn_full | 38% | 30 |

### T2 concept coverage (mean ratio)

| arm | mean coverage | n |
|---|---:|---:|
| baseline | 47% | 15 |
| terse | 65% | 15 |
| caveman_full | 78% | 15 |
| caveman_full_plus_ultra_directive | 83% | 15 |
| hewn_full_v1 | 70% | 15 |
| hewn_full | 53% | 15 |

### T3 concept coverage (mean ratio)

| arm | mean coverage | n |
|---|---:|---:|
| baseline | 5% | 9 |
| terse | 5% | 9 |
| caveman_full | 5% | 9 |
| caveman_full_plus_ultra_directive | 5% | 9 |
| hewn_full_v1 | 27% | 9 |
| hewn_full | 12% | 9 |

### T5 concept coverage (mean ratio)

| arm | mean coverage | n |
|---|---:|---:|
| baseline | 0% | 4 |
| terse | 0% | 4 |
| caveman_full | 0% | 4 |
| caveman_full_plus_ultra_directive | 0% | 4 |
| hewn_full_v1 | 0% | 4 |
| hewn_full | 0% | 4 |

### T4 concept coverage (mean ratio)

| arm | mean coverage | n |
|---|---:|---:|
| baseline | 100% | 20 |
| terse | 95% | 20 |
| caveman_full | 98% | 20 |
| caveman_full_plus_ultra_directive | — | 0 |
| hewn_full_v1 | 100% | 20 |
| hewn_full | 85% | 20 |
