---
name: flint
description: |
  Compresses Claude's answer into Flint, a compact symbolic IR.
  On Claude Opus 4.7 with long-context workloads (codebases, CLAUDE.md,
  RAG), saves ~75% output tokens and ~65% latency vs verbose Claude,
  and +9pt concept coverage (measured on 10 tasks × 4 runs). Good for
  debugging, architecture sketches, code-review risks, and refactor
  specs. Works best on well-scoped technical questions.
allowed-tools: []
---

# Flint skill

You are answering in **Flint**, a compact symbolic IR. Follow the format strictly
for this turn. Do **not** add prose, explanations, code fences, or a human audit.

## Format

```
@flint v0 hybrid
G: <goal atom>
C: <context atoms joined with ∧>
P: <plan atoms with ∧>
V: <verification atoms with ∧>
A: <action atoms with ∧>
```

Rules:
- 5–6 short lines, nothing else.
- Use short `snake_case` atoms.
- Prefer call form `ddl("12 weeks")` over suffix `ddl_"12 weeks"`.
- Echo literal anchors from the user's question verbatim when present
  (numbers, identifiers, code tokens — keep them as-is).
- Connect conjunctions with `∧` only. No commas. No bullets.
- Stop after the `A:` line.

## Example

User asks about a middleware rejecting valid webhooks at timestamp skew of 300s.

Response:
```
@flint v0 hybrid
G: webhook_skew_fix
C: abs(now-ts)>300 ∧ returns("401") ∧ valid_webhook_rejected
P: widen_tolerance ∧ allow_provider_skew ∧ keep_401_on_real_expiry
V: edge(-299s_200) ∧ edge(301s_401) ∧ no_regression
A: adjust_skew_check ∧ add_regression_test
```

## Reading Flint

The response is meant to be precise, not pretty. If you need a readable
rerender later, save the response to a file and run:

```bash
flint-ir audit path/to/response.flint
```

## When not to use

- Open-ended or creative questions (Flint needs a crisp technical goal)
- Long explanations the user actually wants in prose
- Questions where exact literal quoting matters more than structural compression
