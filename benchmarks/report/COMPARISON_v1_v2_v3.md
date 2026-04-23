# Hewn v1 → v2 → v3 comparison

v1 = original (soft prose-caveman directive)
v2 = Codex first attempt (micro-IR auto-routing for Q&A → huge token cuts but concept coverage crashed)
v3 = balance attempt (strict prose-caveman, no auto-IR for Q&A, micro-prose only for vibe/non-tech)

Caveman/baseline/terse arms unchanged — shown for reference.

## T1b — hewn_full v1 → v2 → v3 vs comparators

| prompt | v1 | v2 | v3 | caveman_full | caveman+ultra | baseline |
|---|---:|---:|---:|---:|---:|---:|
| `cors-errors` | 333 | 59 | 175 | 248 | 219 | 423 |
| `debounce-search` | 159 | 59 | 88 | 61 | 53 | 225 |
| `explain-db-pool` | 358 | 56 | 259 | 98 | 62 | 661 |
| `fix-node-memory-leak` | 374 | 59 | 59 | 442 | 319 | 701 |
| `git-rebase-vs-merge` | 158 | 66 | 112 | 103 | 102 | 218 |
| `hash-table-collisions` | 341 | 62 | 231 | 145 | 178 | 309 |
| `queue-vs-topic` | 277 | 74 | 135 | 128 | 122 | 190 |
| `react-rerender-parent` | 214 | 51 | 162 | 140 | 131 | 315 |
| `sql-explain` | 255 | 59 | 120 | 178 | 118 | 266 |
| `tcp-vs-udp` | 173 | 70 | 151 | 125 | 95 | 181 |
| **mean** | **264** | **61** | **149** | **166** | **139** | **348** |

## T2 — hewn_full v1 → v2 → v3 vs comparators

| prompt | v1 | v2 | v3 | caveman_full | caveman+ultra | baseline |
|---|---:|---:|---:|---:|---:|---:|
| `add-search-bar` | 76 | 42 | 51 | 266 | 199 | 197 |
| `login-button-broken` | 236 | 44 | 56 | 122 | 106 | 227 |
| `make-website-faster` | 72 | 43 | 48 | 59 | 131 | 43 |
| `spaghetti-code` | 310 | 55 | 65 | 427 | 451 | 442 |
| `typeerror-undefined-map` | 257 | 56 | 71 | 116 | 105 | 254 |
| **mean** | **190** | **48** | **58** | **198** | **198** | **232** |

## T3 — hewn_full v1 → v2 → v3 vs comparators

| prompt | v1 | v2 | v3 | caveman_full | caveman+ultra | baseline |
|---|---:|---:|---:|---:|---:|---:|
| `body-size-rollout-plan` | 0 | 0 | 3783 | 1927 | 2289 | 5224 |
| `rate-limit-xff-review` | 0 | 0 | 913 | 511 | 536 | 1046 |
| `transfer-handler-review` | 0 | 0 | 1600 | 1233 | 1556 | 1802 |
| **mean** | **0** | **0** | **2098** | **1223** | **1460** | **2690** |

## T5 — hewn_full v1 → v2 → v3 vs comparators

| prompt | v1 | v2 | v3 | caveman_full | caveman+ultra | baseline |
|---|---:|---:|---:|---:|---:|---:|
| `smart-drafts-release-note` | 0 | 0 | 480 | 514 | 515 | 442 |
| `outage-apology-email` | 0 | 0 | 527 | 492 | 493 | 504 |
| **mean** | **0** | **0** | **503** | **503** | **504** | **473** |

## T4 — multi-turn cumulative tokens v1 → v2 → v3

| sequence | v1 | v2 | v3 | caveman_full | baseline |
|---|---:|---:|---:|---:|---:|
| `debug-prod-incident` | 1301 | 353 | 719 | 1612 | 5550 |
| `design-feature` | 5295 | 992 | 4956 | 6840 | 8841 |

## Quality side-by-side

### T1b concept coverage (mean ratio)

| arm | mean coverage | n |
|---|---:|---:|
| baseline | 96% | 30 |
| terse | 96% | 30 |
| caveman_full | 95% | 30 |
| caveman_full_plus_ultra_directive | 93% | 30 |
| hewn_full_v1 | 96% | 30 |
| hewn_full_v2 | 38% | 30 |
| hewn_full | 91% | 30 |

### T2 concept coverage (mean ratio)

| arm | mean coverage | n |
|---|---:|---:|
| baseline | 47% | 15 |
| terse | 65% | 15 |
| caveman_full | 78% | 15 |
| caveman_full_plus_ultra_directive | 83% | 15 |
| hewn_full_v1 | 70% | 15 |
| hewn_full_v2 | 53% | 15 |
| hewn_full | 63% | 15 |

### T3 concept coverage (mean ratio)

| arm | mean coverage | n |
|---|---:|---:|
| baseline | 100% | 9 |
| terse | 100% | 6 |
| caveman_full | 100% | 9 |
| caveman_full_plus_ultra_directive | 98% | 9 |
| hewn_full_v1 | — | 0 |
| hewn_full_v2 | — | 0 |
| hewn_full | 100% | 9 |

### T5 concept coverage (mean ratio)

| arm | mean coverage | n |
|---|---:|---:|
| baseline | 100% | 4 |
| terse | 100% | 4 |
| caveman_full | 100% | 4 |
| caveman_full_plus_ultra_directive | 100% | 4 |
| hewn_full_v1 | — | 0 |
| hewn_full_v2 | — | 0 |
| hewn_full | 100% | 4 |

### T4 concept coverage (mean ratio)

| arm | mean coverage | n |
|---|---:|---:|
| baseline | 100% | 20 |
| terse | 95% | 20 |
| caveman_full | 98% | 20 |
| caveman_full_plus_ultra_directive | 95% | 20 |
| hewn_full_v1 | 100% | 20 |
| hewn_full_v2 | 85% | 20 |
| hewn_full | 82% | 20 |

### T4 transcript-aware concept coverage

Fairer evaluator for multi-turn: judges the FULL conversation not each turn in isolation, so the assistant is not penalized for NOT restating concepts it already established.

| arm | transcript coverage | n |
|---|---:|---:|
| baseline | 100% | 4 |
| terse | 100% | 4 |
| caveman_full | 100% | 4 |
| hewn_full_v1 | 100% | 4 |
| hewn_full_v2 | 100% | 4 |
| hewn_full | 100% | 4 |
