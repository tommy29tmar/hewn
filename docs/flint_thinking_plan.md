# Plan — Flint thinking mode (always-on dual-mode)

**Status:** drafted 2026-04-18 (evening). Execution window: Monday 2026-04-20.
**Owner:** Tommaso.
**Risk:** medium. Prompt-level change with bench validation gate before promotion.

---

## Context

Current Flint (v0.3.0) ships as a **strict-output** IR. It wins hard on
task-shape workloads (186 tok / 5s / 95% coverage on Opus 4.7 stress bench)
but cannot be left always-on like Caveman: on open-ended / long-form tasks
it either crams everything into slot `A:` (illegible) or silently
violates the format.

Caveman stays on because it's a *descriptive* constraint ("terse prose, drop
articles"). It degrades gracefully on any task shape. Flint's structural
contract breaks ungracefully.

## Goal

Ship **Flint thinking mode**: a system-prompt variant that makes Flint safe
as an always-on replacement for Caveman, by splitting compression by
**audience**:

- **Default / user-facing text** → compact natural prose (Caveman-lite).
- **Internal LLM reasoning** (tool planning, chain-of-thought scratchpads,
  observation interpretation) → Flint IR.
- **Deliverables for humans** (plans, RFCs, PR descriptions, docs, code
  walkthroughs) → always prose, never IR.

Success = 186 / 5s / 95% on the task-shape bench **and** zero IR leak on a
new open-ended corpus.

## Non-goals (explicitly out of this phase)

- Replacing the v0.3.0 strict prompt immediately. Ship as a new variant
  first; promote only if bench holds on both corpora.
- Multi-turn context-accumulation benchmark (measuring how hidden `<reasoning>`
  blocks reduce cumulative context cost across turns). Tracked separately.
- Migrating the 4 existing slash commands semantics. Flint-on / Flint-off
  stay; may get renamed / deprecated if thinking-mode becomes default.

## Deliverables

1. `integrations/claude-code/flint_thinking_system_prompt.txt` — new prompt
   (~20–30 lines) defining the three zones.
2. `integrations/claude-code/output-styles/flint-thinking.md` — second output
   style so users can try it via `/config` → Output style → `flint-thinking`.
3. `scripts/run_stress_bench.sh` — add 4th cell `flint_thinking`.
4. `scripts/stress_table.py` — include the new cell in the output table.
5. `evals/tasks_open_ended.jsonl` — NEW corpus of 8–10 open-ended tasks
   (essays, brainstorms, RFC writeups, code walkthroughs). Used as the
   "must fall back to prose" test.
6. `scripts/run_fallback_bench.sh` + `scripts/fallback_table.py` — harness
   that runs the 3 existing variants + flint_thinking on the open-ended
   corpus and reports **% of responses starting with `@flint v0`**.
7. Decision & artifact:
   - **Promote**: flint_thinking becomes default → v0.4.0, updated docs,
     updated README claim, launch post drafts refreshed.
   - **Iterate**: findings recorded in `docs/flint_thinking_iteration_notes.md`,
     ship flint_thinking as optional variant, try again later.

## Acceptance criteria

### On `tasks_stress_coding.jsonl` (existing task-shape corpus)

- `flint_thinking` output tokens ≤ **220** (current 186, 15% slack allowed).
- `flint_thinking` must_include coverage ≥ **90%** (current 95%, 5pt slack).
- ≥ 90% of flint_thinking responses must be **parseable Flint**
  (`flint validate` exits 0).

### On `tasks_open_ended.jsonl` (new open-ended corpus)

- **0%** of flint_thinking responses emit strict IR as the user-facing body
  (regex check: user-visible response must not start with `@flint v0` after
  any optional `<reasoning>...</reasoning>` block is stripped).
- Output tokens ≤ Caveman's on the same corpus (so we're at least as good
  as Caveman on the tasks Caveman was designed for).

### Format discipline

- On shape tasks: response structure is G/C/P/V/A or mixed (IR+prose audit).
- On open-ended tasks: response structure is terse prose, no "exploded IR"
  (single slot with 10+ atoms).

## Plan of execution

### Step 1 — design prompt (est. 1h)

Draft `flint_thinking_system_prompt.txt`. Three zones made explicit:

```
DEFAULT USER-FACING STYLE
- terse natural prose. drop filler. keep literals exact.
- code fences ok. 1 idea per line. match length to task.

INTERNAL REASONING
- when planning tool calls or analyzing observations, emit Flint IR
  inside <reasoning>...</reasoning>:
    G: ... / C: ... / P: ... / V: ... / A: ...
- treat <reasoning> as your scratchpad, not deliverable.

DELIVERABLES FOR HUMANS
- plans, PR descriptions, RFCs, docs → always prose.
- if the user asks for an IR-shape answer (debug/review/refactor/
  architecture with a crisp goal), emit Flint as user-facing.
- never emit Flint for a task whose natural output is an artefact
  a human reviews word-by-word.

Default: prose. Flint for thinking. Strict IR only when user's
question is itself task-shape.
```

Test manually on 3 crisp tasks (debug, review, refactor) + 3 open-ended
(explain GCs, brainstorm ideas, write RFC). Iterate until qualitatively
correct before running the bench.

**Output of Step 1:** `flint_thinking_system_prompt.txt` committed to
`integrations/claude-code/`, manually sanity-checked.

### Step 2 — integrate into bench (est. 30min)

- Add this line to `scripts/run_stress_bench.sh`:
  ```bash
  run_cell "flintthinking" "sigil" "integrations/claude-code/flint_thinking_system_prompt.txt" "$i" 512 &
  ```
- Add to `CELLS` in `scripts/stress_table.py`:
  ```python
  ("Flint (thinking)", "stress_flintthinking"),
  ```
- Dry-run: `RUNS=1 ./scripts/run_stress_bench.sh` → table renders 4 rows.

### Step 3 — write open-ended corpus (est. 1h)

Create `evals/tasks_open_ended.jsonl` with 8 tasks, mixing:

| id | category | task |
| --- | --- | --- |
| explain-gc-generational | explanation | "Spiega come funzionano i garbage collector generazionali in prosa." |
| brainstorm-pubsub-latency | brainstorm | "Dammi 5 idee per ridurre la latenza p95 in un sistema pub/sub interno." |
| rfc-user-schema-change | deliverable | "Scrivi una RFC per migrare users.email da VARCHAR(100) a VARCHAR(320)." |
| walkthrough-parser | walkthrough | "Spiega questo parser.py riga per riga." (+ paste of src/flint/parser.py) |
| opinion-design-choice | subjective | "Questo design a eventi è ragionevole per un team di 3?" (+ context) |
| tutorial-prompt-cache | tutorial | "Scrivimi un tutorial di 500 parole su prompt caching." |
| long-debug-narrative | debug-narrative | "Debugga questo outage con stack trace completo" (+ 2k tok of logs) |
| pr-description | deliverable | "Scrivi una PR description per questo diff." (+ diff) |

Each task has `must_include` keywords and a `format_check` field: either
`"prose"` (Flint must not leak) or `"ir_ok"` (IR is acceptable).

### Step 4 — write fallback harness (est. 30min)

- Copy `run_stress_bench.sh` → `run_fallback_bench.sh`. Swap `TASKS` to
  `evals/tasks_open_ended.jsonl`, output dir to `evals/runs/fallback/`.
- Copy `stress_table.py` → `fallback_table.py`. Add metric:
  ```python
  ir_leak_rate = sum(1 for r in rows if r["content"].lstrip().startswith("@flint v0")) / len(rows)
  ```
  Print it as a new column.

### Step 5 — run both benches (est. 30min wall-clock)

```bash
RUNS=4 ./scripts/run_stress_bench.sh
python3 scripts/stress_table.py
RUNS=4 ./scripts/run_fallback_bench.sh
python3 scripts/fallback_table.py
```

Cost estimate: ~$4–5 of Opus 4.7 credits total.

### Step 6 — analyze & decide (est. 1h)

Three branches:

| outcome | action |
| --- | --- |
| Shape pass + open-ended pass | **Promote**: go to Step 7. |
| Shape pass, open-ended fail (IR leaks) | Iterate prompt. Re-run Steps 1, 5, 6 with a tightened heuristic. |
| Shape fail (bench numbers drop) | Check if fallback is firing inappropriately. Tighten "is this task IR-shape?" detection in prompt. Re-run. |

Budget max 2 iterations. If 3rd run still fails, park and document.

### Step 7 — ship or park (est. 30min)

**If promote:**
- Copy `flint_thinking_system_prompt.txt` → `flint_system_prompt.txt` (replace).
- Update installer to install the thinking-mode prompt as default output-style body.
- Update README hero section: "Caveman, ma sa ragionare" / "Flint: always-on, Caveman-shape prose + Flint-shape IR".
- Update `docs/methodology.md`, `docs/architecture.md`, `docs/failure_modes.md`.
- Update `integrations/claude-code/skills/flint-on/SKILL.md` to describe the
  *strict* mode opt-in (opt-out of the default thinking mode).
- Update launch posts in `prompts/launch_posts/` with new framing.
- Bump version 0.3.0 → **0.4.0**.
- Commit: *"Promote Flint thinking mode to default; v0.4.0"*.
- Tag: `v0.4.0`. Push main + tag.

**If park:**
- Keep `flint_thinking_system_prompt.txt` in repo as experimental variant.
- Document findings in `docs/flint_thinking_iteration_notes.md`: what
  tried, what broke, open questions.
- Commit: *"Experimental flint_thinking variant; park for next iteration"*.
- No version bump, no tag.

## Rollback

If post-promotion real users report regressions (their `/flint` or
`/flint-on` workflow breaks), revert via:

```bash
git revert <promote-commit>
git push origin main
```

Skills contract stays: 4 slash commands, same semantics. Only the default
system prompt changes.

## Open decisions (resolve on Monday)

1. **Explicit `<reasoning>` tags, or implicit split?**
   Test both variants in Step 1 manually. Pick the one the model
   consistently honors.
2. **`/flint-on` semantic shift.** Currently = "strict IR always". After
   promotion = "switch from thinking-mode to strict IR". The skill body
   needs a one-line rewrite in Step 7.
3. **Version bump: 0.4.0 or 1.0.0?** Default is 0.4.0. Bump to 1.0.0 only
   if we're ready to commit to backward-compatibility from that point.
   Current call: 0.4.0, keep research velocity.

## Acceptance signal

Plan is considered done when:
- Both benches are committed with green numbers (if promoting)
- Or: iteration notes + experimental prompt are committed (if parking)
- Either way: `git status` clean, tests 73/73 green, branch pushed.

## Time budget

5–7h focused work. ~$4–5 API spend. One afternoon, cleanly.

## Files touched summary (for git diff preview Monday morning)

Created:
- `integrations/claude-code/flint_thinking_system_prompt.txt`
- `integrations/claude-code/output-styles/flint-thinking.md`
- `evals/tasks_open_ended.jsonl`
- `scripts/run_fallback_bench.sh`
- `scripts/fallback_table.py`
- (maybe) `docs/flint_thinking_iteration_notes.md`

Modified:
- `scripts/run_stress_bench.sh` (+1 cell)
- `scripts/stress_table.py` (+1 row)

If promote, also modified:
- `integrations/claude-code/flint_system_prompt.txt` (content swap)
- `README.md`, `docs/methodology.md`, `docs/architecture.md`,
  `docs/failure_modes.md`, `docs/faq.md`
- `pyproject.toml`, `src/flint/__init__.py` (0.3.0 → 0.4.0)
- `prompts/launch_posts/*.md` (updated framing)
