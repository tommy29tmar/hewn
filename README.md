# Flint

**Caveman prompts. Flint delivers.**

Claude answers in 6 lines instead of 872. -54% tokens. -73% latency. Same concepts, preserved.

![demo](assets/launch/demo.png)

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/tommy29tmar/flint/main/integrations/claude-code/install.sh | bash
```

Then in Claude Code:

```
/flint <your technical question>     # one-shot
/output-style flint                   # every response, Flint format
```

Turn it off: `/output-style default`.

## Why it works

Most token-saving tricks save tokens by telling Claude to drop words. That works until Claude also drops the concepts you needed.

Flint doesn't compress the words. It compresses the **shape** of the answer into 5 slots:

- **G** — the goal
- **C** — the context and constraints
- **P** — the plan
- **V** — how to verify it
- **A** — the action to take

One operator, `∧`. Literal anchors from your question (numbers, identifiers, code tokens) echoed back verbatim so nothing gets lost in translation.

That's it. Six lines. Same concepts. Less than half the tokens.

## Proof

Benchmark on Claude Opus 4.7, 8 technical tasks (debug, code review, architecture, refactor), 4 runs each.

| approach                    | tokens | latency | concepts covered |
|-----------------------------|-------:|--------:|-----------------:|
| Claude default (verbose)    |    905 |   12.4s |              80% |
| Caveman ("primitive English")|    441 |    4.9s |              72% |
| "Be concise, return JSON"   |    439 |    4.9s |              76% |
| **Flint**                   | **415** | **3.3s** |          **78%** |

Flint wins on every column. The only approach that matches verbose Claude on concept coverage — at less than half the cost.

## Flint vs Caveman

You've probably seen "Caveman prompting" — tell Claude to drop articles and filler, save ~50% tokens. It works, but Claude also drops concepts. On this bench, Caveman loses 8 points of concept coverage. You pay for the savings in answer quality.

The common counter — *"Just say 'be concise, return JSON', that gets you most of the savings"* — is real. We benched it too. It does save tokens. It also loses 4 points of concept coverage and stays 33% slower than Flint.

Flint compresses the **structure**, not the content. That's why the concepts survive. Caveman gives you grunts. Flint gives you the answer.

## When things drift

Claude sometimes drifts off format. Flint ships with a parser, a repair layer, and `flint audit --explain` that shows you exactly what came in, what was repaired, which anchors matched, and a prose rerender — so you can trust the output even on the worst cases.

```bash
flint audit --explain response.flint --anchor 300 --anchor 401
```

## Reproduce the numbers

```bash
git clone https://github.com/tommy29tmar/flint && cd flint
cp .env.example .env && $EDITOR .env      # ANTHROPIC_API_KEY
./scripts/run_caveman_bench.sh             # 4 runs per cell, ~2 min
python3 scripts/caveman_table.py
```

Set `RUNS=1` for a quick single-shot run. Full methodology and cross-model data in [docs/research.md](docs/research.md).

## Honest scope

Flint shines on crisp technical asks: debug this, review this diff, refactor this function, sketch this architecture. It's not for open-ended writing. Use Claude normally for that.

## License

MIT. If you cite Flint in research, see [CITATION.cff](CITATION.cff).
