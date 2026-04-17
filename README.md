# SIGIL

**Claude answers in 6 lines instead of 872. Concepts preserved. -54% tokens. 73% faster.**

![demo](assets/launch/demo.png)

## What it does

SIGIL compresses Claude's answer into a structured 6-line format — no prose, no headers, no filler. Same concepts, a fraction of the tokens.

Ask Claude to debug a webhook timestamp check. Without SIGIL, you get an 872-token essay with sections, code blocks, and "Root Cause" headers. With SIGIL:

```
@sigil v0 hybrid
G: fix_skew
C: webhook_verify ∧ "300" ∧ "401" ∧ edge_reject
P: widen_window ∧ provider_skew_only ∧ min_fix ∧ reg_test
V: valid_webhook_passes ∧ stale_still_401
A: patch_tolerance ∧ add_reg_test
```

Six lines. Goal, Context, Plan, Verification, Action. Every literal anchor from the question (`300`, `401`) echoed verbatim. Parseable by `sigil audit` if you want a prose rerender.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/tommy29tmar/SIGIL/main/integrations/claude-code/install.sh | bash
```

Then in Claude Code:

```
/sigil <your technical question>     # one-shot
/output-style sigil                   # every response in SIGIL
```

Turn it off: `/output-style default`.

## Benchmark (Opus 4.7, 8 technical tasks, averaged over 4 runs)

| variant                     |       tokens |        latency |     must_include |
|-----------------------------|-------------:|---------------:|-----------------:|
| default (verbose)           |  905.1 ± 22  |  12.4s ± 0.2   |    79.9% ± 1.6   |
| Caveman (primitive English) |  441.3 ± 15  |   4.9s ± 0.3   |    72.1% ± 1.8   |
| "Be concise, return JSON"   |  438.8 ± 11  |   4.9s ± 0.3   |    75.8% ± 5.3   |
| **SIGIL**                   | **415.2 ± 6**| **3.3s ± 0.1** | **78.1% ± 1.5**  |

Against verbose Claude, SIGIL saves **-54% tokens** and cuts latency **-73%**. `must_include` sits within 2pt of verbose — statistically tied on this sample — while every other compression approach drops 4–8pt.

## SIGIL vs Caveman, head-to-head

Caveman-style prompts ("no articles, no filler, primitive English") are the popular token-compression trick. On the same 8-task holdout, Caveman saves ~51% tokens but drops `must_include` from 80% to 72% — saving tokens by cutting concepts.

The skeptic's reply: *"'Be concise, return JSON' already gets you most of the savings."* True — that control saves ~51% too, with 76% `must_include`. Real, honest number. We added it to the table above so you don't have to guess.

Against both controls, SIGIL still wins:

- **-5% tokens vs either control** (415 vs 439/441)
- **-33% latency** (3.3s vs 4.9s — single biggest practical difference)
- **+2pt must_include vs concise-JSON**, **+6pt vs Caveman**

And where Caveman is vibes-based prompting, SIGIL ships an actual IR with a grammar, a parser, a local repair layer, and `sigil audit --explain` — so when Claude drifts off format, you get the answer back repaired, not garbage.

## Debug any SIGIL response

```bash
sigil audit --explain response.sigil --anchor 300 --anchor 401
```

Five side-by-side panels — raw, repaired, parse state, anchor hit/missed, prose audit.

## Scope honest

SIGIL shines on crisp technical tasks: debugging, code review, refactors, architecture sketches. It doesn't try to compress open-ended prose, and shouldn't. For long answers, use Claude normally.

## Run the benchmark yourself

```bash
git clone https://github.com/tommy29tmar/SIGIL && cd SIGIL
cp .env.example .env && $EDITOR .env     # add ANTHROPIC_API_KEY
./scripts/run_caveman_bench.sh            # 4 runs per cell, ~2 min
python3 scripts/caveman_table.py
```

Set `RUNS=1` for a quick single-shot run.

Full methodology and cross-model runs in [docs/research.md](docs/research.md).

## License

MIT. If you cite SIGIL in research, see [CITATION.cff](CITATION.cff).
