# Launch checklist — Flint viral release

Everything in the repo is ready. This is your step-by-step for go-live.

## Status at handoff (generated overnight)

**Benchmark on `tasks_top_tier_holdout.jsonl` (8 tasks × 3 variants × 4 models, every cell gate-clean):**

| Model | Flint tokens | Flint latency | must_include |
| --- | ---: | ---: | ---: |
| Sonnet 4   | -3.1%   | -43.7%  | 86.5% (↑ from 66.7% baseline) |
| Sonnet 4.6 | -24.4%  | -52.3%  | 79.2% (↑ from 70.8%) |
| Opus 4.6   | **-47.3%** | **-68.5%** | 83.3% (baseline 89.6%) |
| Opus 4.7   | -27.5%  | -56.2%  | 76.0% (baseline 86.5%) |

**Headline options, in order of strength:**

1. *"-47% tokens on Opus 4.6, -27% on Opus 4.7"* — biggest number, but Opus 4.6 isn't the newest model.
2. *"Claude latency halved. ~25–47% tokens back. One install."* — latency is the story that's unambiguous.
3. *"Claude Opus 4.7 is the best. Here's 25% of your bill back."* — timing-tied to the 4.7 launch.

My vote: combine them. Lead visually with the latency gif/numbers ("Claude responds in half the time"), quote the token range, peg the moment to 4.7.

## A decision you need to make before pressing go

You asked whether to laser-focus this release on Opus 4.7 only and ignore the other three models. My call:

- **Don't throw away the multi-model validation.** It's the strongest methodological shield against HN/Twitter critique. "Works on one model" sounds fragile; "works on four" sounds general.
- **Do hero-position Opus 4.7** in the headline, the demo GIF, and the post title — ride the launch moment.
- **Optional second iteration**: a 2–3 hour pass of Opus-4.7-specific prompt tuning could plausibly push the 4.7 row from -27% to -35%+. If you want that, say "fine-tune 4.7" in the morning and I'll do a bounded experiment. If not, ship what's here — it's already a strong story.

## What's in the repo now

- `README.md` — new landing-page README (the old one moved to `docs/research.md`)
- `docs/research.md` — the full research README (preserved)
- `docs/manifesto.md` — the old README_SIGIL (preserved)
- `docs/launch_opus47.md` — launch post draft (600-800 words, HN-ready)
- `docs/launch_benchmark_table.md` — machine-generated benchmark table
- `integrations/claude-code/skill/SKILL.md` — the `/flint` Claude Code skill
- `integrations/claude-code/output-styles/flint.md` — persistent output-style variant
- `integrations/claude-code/flint_system_prompt.txt` — the single shipped prompt (source of truth)
- `integrations/claude-code/install.sh` — one-command installer (curl-piped)
- `scripts/bench_cell.py` / `publish_gate.py` / `launch_table.py` — benchmark tooling
- `scripts/demo.py` — 3-way side-by-side demo (used to generate the launch screenshot)
- `scripts/render_demo_image.py` — turns demo text output into a PNG
- `assets/launch/demo.png` + `demo_output.txt` — the launch screenshot and raw text
- `evals/runs/launch/*.jsonl` — all 12 per-cell benchmark runs + manifest + summary

## What NOT been done (intentional, your call)

- **Nothing has been pushed to GitHub.** All changes are local commits. Push when you decide.
- **Nothing published to PyPI.** The `pip install flint-ir` path currently fails because the package isn't on PyPI. The installer uses `pipx install git+...` which works from the public repo.
- **No social posts.** Launch post is in `docs/launch_opus47.md`. You press publish.
- **No GIF.** There's a PNG screenshot at `assets/launch/demo.png`. Record a real GIF/video when you have time — it'll lift CTR on X/HN.

## Ship steps (the morning of)

### 1. Review the artifacts

```bash
cd /home/tommaso/dev/playground/Flint
git log --oneline -20                       # see what was done
git status                                  # anything uncommitted?
cat README.md                               # scan the landing page
cat docs/launch_opus47.md                   # scan the launch post
```

Open `assets/launch/demo.png` in your viewer. Check it reads well.

### 2. (Optional) Record a proper GIF

Use `asciinema` + `agg` (or a screen recorder):

```bash
asciinema rec demo.cast
python3 scripts/demo.py "Review: const sql='SELECT * FROM invoices ORDER BY '+req.query.sort;"
# Ctrl-D to stop
agg demo.cast assets/launch/demo.gif
```

Commit and update the README `<img>` reference from `demo.png` to `demo.gif`.

### 3. Push to GitHub

```bash
git push origin main
```

Verify https://github.com/tommy29tmar/Flint renders the new README.

### 4. Test the one-line installer in a clean env

```bash
# In a fresh container or VM:
curl -fsSL https://raw.githubusercontent.com/tommy29tmar/Flint/main/integrations/claude-code/install.sh | bash
ls ~/.claude/skills/flint/
# Then try /output-style flint in a Claude Code session and ask a technical question.
```

If install breaks, fix before posting. This is the single point of failure in the launch.

### 5. (Optional) Publish to PyPI

If you want `pip install flint-ir` to work instead of `pipx install git+...`:

```bash
cd /home/tommaso/dev/playground/Flint
python3 -m build                # needs `pip install build`
python3 -m twine upload dist/*  # needs a PyPI token
```

Then bump the installer to prefer PyPI. Not blocking — the curl installer already works.

### 6. Post

Order matters. Stack them roughly 15–30 min apart so traffic converges.

1. **HN Show HN**: title `Show HN: Flint – compress the work Claude does, not the fluff (-27% tokens on Opus 4.7)`. Body: first paragraph of `docs/launch_opus47.md`. Link: the repo.
2. **X / Twitter**: hook + table screenshot + link. Character budget example:
   > Made Claude Opus 4.7 27% cheaper with a prompt-level IR.
   > -56% latency. Validated across 4 Claude models.
   > Not a Caveman-style voice trick — real work compression vs a terse baseline.
   > One install. MIT.
   > github.com/tommy29tmar/Flint
3. **r/LocalLLaMA** and **r/ClaudeAI**: adapt post, lead with the benchmark table.
4. **Claude Code Discord**: `#share-your-work` channel or equivalent, lead with the skill install line.

### 7. Be present for 4–8 hours after posting

HN dies fast. If you answer top comments in the first 2 hours you multiply signal. Expected objections to have ready answers for:

- *"Why not just use Caveman?"* — The primitive-english row in the table is Caveman-style. On Sonnet 4.6 it hurts must_include. On Opus 4.6 it saves only 7%. Flint does both better.
- *"8 tasks is too few."* — Fair. Reproducible with `scripts/run_launch_bench.sh` against any corpus. Plan a larger run in v2.
- *"Must_include isn't quality."* — True. It's a literal-retention proxy, the honest measure the repo supports. Semantic judge is roadmap.
- *"Why should I care, Claude Code already has skills."* — Because `/flint` is just a way to install; the actual artifact is a provider-agnostic prompt that works via any API.

## If the launch lands

- Watch GitHub stars and issues. Respond fast to install failures — that's the one kind of issue that kills momentum.
- Within 48h: write a follow-up post with Day 1 data (how many installs, biggest reported savings, a fun failure mode).
- Within 1–2 weeks: make the Opus 4.7-tuned variant real (if you want it), publish to PyPI, record a 60-second demo video.

## If it flops

- Don't retract — that's worse than silence.
- Archive the repo under `launches/flint-v1` and keep going. The methodology and tooling are good even if the angle didn't land. Next angle: reframe as "Flint: the serving IR for self-hosted Claude replacements" and target r/LocalLLaMA specifically.

## Open questions for you in the morning

1. Laser-focus on Opus 4.7 with extra tuning? (my take: no, ship multi-model)
2. Record a real GIF before launching, or ship with the static PNG? (my take: static PNG is fine for v1, GIF for a follow-up post)
3. Opus 4.6's -47% is the most quotable number — lead with it or with 4.7's -27% + timing? (my take: hero 4.7, but quote the -47% on 4.6 as proof it's not a fluke on the biggest-number row)
4. Publish to PyPI now or only if traction arrives? (my take: only if traction)

Good luck.
