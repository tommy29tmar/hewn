# Claude Opus 4.7 is the best. Here's 25–47% of your bill back.

*Ship date: TBD. Draft for HN/X/Reddit/Discord launch.*

Opus 4.7 just landed. It's the smartest Claude yet. It's also the priciest. On complex technical queries, the API bill climbs fast.

So I shipped **Flint**, a tiny open-source skill for Claude Code that compresses Claude's output into a compact symbolic IR. On a hard 8-task holdout across debugging, architecture, security review, and refactoring:

- **Opus 4.7:** -27% tokens, -56% latency
- **Opus 4.6:** -47% tokens, -68% latency
- **Sonnet 4.6:** -24% tokens, -52% latency
- **Sonnet 4:** -3% tokens, -44% latency (and *higher* must_include than baseline)

All four rows validated on the same corpus, same protocol. Install is one command.

```bash
curl -fsSL https://raw.githubusercontent.com/tommy29tmar/Flint/main/integrations/claude-code/install.sh | bash
```

Then in Claude Code: `/output-style flint`. Done.

## What it does, concretely

Normal Claude answers the SQL-injection review question like this:

> **Risk:** SQL injection via `req.query.sort`. Attacker can append arbitrary SQL (e.g. `id; DROP TABLE invoices--`)… **Mitigation:** Whitelist allowed columns and directions… **Verification:** Unit tests with malicious input, static analysis…

611 output tokens on Opus 4.7, 11 seconds.

Flint answers it like this:

```
@flint v0 hybrid
G: harden_sort_param
C: sql_injection ∧ ORDER_BY ∧ req.query.sort ∧ string_concat
P: allowlist_columns ∧ map_to_identifier ∧ validate_direction_asc_desc
V: unit_tests_malicious_input ∧ sqli_fuzz ∧ static_analysis_taint
A: replace_concat_with_allowlist ∧ parameterize_or_quote_identifier ∧ add_regression_tests
```

185 output tokens, 3.9 seconds. **-45% tokens, -64% latency, same information content.**

## Why this isn't Caveman

Every compression project on the timeline eventually gets compared to [Caveman](https://gist.github.com/simonw/... or wherever) — the prompt-style trick where you tell Claude to talk like a caveman: no articles, no "Certainly!", no filler. Caveman can claim 50–60% savings, but that's because it measures itself against verbose default Claude. Most of what it cuts is stylistic fluff.

I measured Flint against an **already-terse baseline** — a system prompt that tells Claude to be concise in plain English. On top of that terse baseline, the additional savings are still ~25% tokens and half the latency. That's real compression of the work, not the voice.

In the same benchmark I also ran a primitive-English variant (the Caveman-style comparable). Results are in the repo. On Sonnet 4.6 it actually hurt quality — the must_include rate dropped from 70.8% → 61.5%, because dropping articles doesn't preserve technical specificity. Flint's symbolic IR keeps it.

## The benchmark

One corpus (`tasks_top_tier_holdout.jsonl`, 8 tasks), one protocol, three variants per model, every cell gated for truncation and completeness before it lands in the table:

| Model       | Variant            | Avg total tokens | vs terse     | Latency vs terse | must_include |
| ----------- | ------------------ | ---------------: | -----------: | ---------------: | -----------: |
| Sonnet 4    | terse              |              350 |           —  |               —  |        66.7% |
| Sonnet 4    | **flint**          |          **339** |    **-3.1%** |      **-43.7%**  |    **86.5%** |
| Sonnet 4.6  | terse              |              504 |           —  |               —  |        70.8% |
| Sonnet 4.6  | **flint**          |          **381** |   **-24.4%** |      **-52.3%**  |    **79.2%** |
| Opus 4.6    | terse              |              693 |           —  |               —  |        89.6% |
| Opus 4.6    | **flint**          |          **365** |   **-47.3%** |      **-68.5%**  |    **83.3%** |
| Opus 4.7    | terse              |              667 |           —  |               —  |        86.5% |
| Opus 4.7    | **flint**          |          **484** |   **-27.5%** |      **-56.2%**  |        76.0% |

Opus 4.6 is the biggest row — -47% tokens, -68% latency. Opus 4.7 has a tighter baseline (it's already more efficient by default), so the absolute win is smaller but still substantial. Sonnet 4's token savings are modest on this corpus but the latency gain is huge and must_include actually improves.

## How it's built

- **A formal grammar.** EBNF at `grammar/flint.ebnf`, parser at `src/flint/parser.py`, all stdlib.
- **A local repair layer.** The model can drift (whitespace, case, quoting); `src/flint/normalize.py` canonicalizes before the parser sees it.
- **A verifier.** Must-include literals and exact literals are checked locally — the eval is not grading the prompt on vibes.
- **Stop sequences on the wire.** The API stops at `[AUDIT]`, so the re-readable audit doesn't burn output tokens.
- **A single unified system prompt.** 8 lines. `integrations/claude-code/flint_system_prompt.txt`. This is the shippable artifact; the benchmark measures exactly this file.

## What I'm *not* claiming

- I'm not claiming end-to-end Claude Code savings. CC adds its own system prompts and tool loops that I don't control. The benchmark measures the Flint system prompt on the Anthropic Messages API, which is what the skill injects.
- I'm not claiming zero quality loss. must_include is a literal-retention proxy, not a semantic-correctness grade. It's what was measurable without an LLM judge.
- I'm not claiming this works on creative or open-ended tasks. It doesn't, and it shouldn't.

## Why it exists

I wanted to see if you could treat prompting like compiler design: freeze the grammar, freeze the IR, benchmark the artifact, ship that exact artifact. The answer, for now, is yes — on technical Q&A against a serious baseline, with a tiny piece of local tooling, you can take a quarter off your Claude bill without a subscription, a proxy, or a rewrite.

If you're burning money on Opus 4.7, try it and tell me where it breaks.

---

**Repo:** https://github.com/tommy29tmar/Flint
**Skill install:** one `curl | bash` above
**Benchmark:** `./scripts/run_launch_bench.sh claude-opus-4-7 opus47 && python3 scripts/launch_table.py evals/runs/launch/manifest.json`
**License:** MIT
