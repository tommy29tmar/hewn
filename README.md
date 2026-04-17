# SIGIL

**Claude answers in 6 lines instead of 872. Concepts preserved. -54% tokens. 70% faster.**

![demo](assets/launch/demo.png)

## What it does

SIGIL compresses Claude's answer into a structured 6-line format — no prose, no headers, no filler. Same concepts, a fraction of the tokens.

Ask Claude to debug a webhook timestamp check. Without SIGIL, you get an 872-token essay with sections, code blocks, and "Root Cause" headers. With SIGIL:

```
@sigil v0 hybrid
G: webhook_skew_fix
C: abs(now-ts)>300 ∧ returns("401") ∧ valid_webhook_rejected
P: widen_tolerance ∧ allow_provider_skew ∧ keep_401_on_real_expiry
V: edge(-299s_200) ∧ edge(301s_401) ∧ no_regression
A: adjust_skew_check ∧ add_regression_test
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

## Benchmark (Opus 4.7, 8 technical tasks)

| variant             | tokens | latency | must_include |
|---------------------|-------:|--------:|-------------:|
| default (verbose)   |    905 |   12.6s |          80% |
| Caveman (primitive) |    460 |    5.6s |          66% |
| **SIGIL**           |    413 |    3.8s |      **82%** |

Against verbose Claude, SIGIL saves **-54% tokens** and cuts latency **-70%**.

## SIGIL vs Caveman

Caveman-style prompts ("no articles, no filler, primitive English") are the other popular token-compression trick. On the **same 8-task holdout**, Caveman saves -49% tokens but **drops must_include from 80% to 66%** — it's saving tokens by cutting concepts.

SIGIL saves **more tokens (-54%)** and posts **higher must_include on the same corpus (82%)**. It compresses structure, not meaning. And where Caveman is a vibes-based prompting style, SIGIL is an actual IR with a grammar, a parser, and a local repair layer — so when Claude drifts off format, you get the answer repaired, not garbage.

## Debug any SIGIL response

```bash
sigil audit --explain response.sigil --anchor 300 --anchor 401
```

Prints 5 side-by-side panels — raw, repaired, parse state, anchor hit/missed, prose audit — so you can trust what SIGIL gave you even when the model drifts off format.

## Scope honest

SIGIL shines on crisp technical tasks: debugging, code review, refactors, architecture sketches. It doesn't try to compress open-ended prose, and shouldn't. For long answers, use Claude normally.

## Run the benchmark yourself

```bash
git clone https://github.com/tommy29tmar/SIGIL && cd SIGIL
cp .env.example .env && $EDITOR .env     # add ANTHROPIC_API_KEY
./scripts/run_caveman_bench.sh
python3 scripts/caveman_table.py
```

Full methodology and cross-model runs in [docs/research.md](docs/research.md).

## License

MIT. If you cite SIGIL in research, see [CITATION.cff](CITATION.cff).
