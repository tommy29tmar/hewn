# Plan — Flint Thinking Mode (always-on dual-mode) — v4

v4 changelog (vs v3, Codex R3 feedback):
- **R3.1 A4 layout-independence.** v3 scanned `lines[1:10]` for slot headers, which false-fails valid `@flint v0 hybrid` docs that include an optional `@cb[...]` codebook (parser.py:239; `examples/debugging.flint` uses one, pushing P/V/A past line 10). v4 parses first, then asserts on the parsed `Document`: `header.mode == "hybrid"`, required clause tags `{G, C, P, V, A} ⊆ {c.tag for c in document.clauses}`. Pure parser-and-header test; no layout assumption.
- **R3.2 Boundary tasks replaced again.** Codex R3 correctly flagged that v3's two prose-side replacements (`feedback-on-code-quality` with attached `scraper.py`, `sanity-check-mutex-approach`) both resolve to IR under the product's own rule: the README (`README.md:104`) and skill doc (`integrations/claude-code/skills/flint/SKILL.md:7`) explicitly market Flint for "review this diff" and architecture choice asks. v4 replaces both with tasks whose body **explicitly disavows a verifiable endpoint** ("non voglio un fix", "non cerco una decisione"), making them genuinely narrative despite concrete-tech surface.

v3 changelog (vs v2, Codex R2 feedback):
- **R2.1 A4 header tightened.** Parser's `HEADER_RE` (parser.py:11) accepts `@flint v0 audit` or bare `@flint v0`. v2's A4 regex `^@flint\s+v\d+\b` passed all of them. v3 required exact `@flint v0 hybrid` header + version/mode assertion on parsed document. (v4 builds on this, see R3.1.)
- **R2.2 Boundary tasks replaced.** Codex flagged 2 of 4 v2 boundary tasks as not actually borderline. (v4 replaces them again — see R3.2.)

v2 changelog (vs v1, Codex R1 feedback):
- **R1.1 Transport fix:** `flintthinking` bench cell now uses `plain` transport (not `sigil`). Raw model output is persisted as-is; no stop sequences, no `materialize_direct_sigil` normalization, no synthetic `[AUDIT]` injection. All gates compute on raw `content`.
- **R1.2 A4 check:** defined independently of the shipped `flint validate` (which only requires ≥1 clause — confirmed by reading `src/flint/parser.py:291-299`). A4 now uses a bench-local strict check that asserts all 5 slot headers + `@flint v` header present in the first 10 lines of raw output.
- **R1.3 Boundary subset:** added 4 borderline tasks inside `tasks_open_ended.jsonl` with explicit `expected_shape ∈ {"ir", "prose"}`. Classification accuracy is a separate gate (C).
- **R1.4 Rerun policy:** any prompt edit invalidates both corpora. Iteration uses cheap smoke runs (RUNS=1); the shipped prompt must pass one final clean RUNS=4 on both benches. Removed the "<3% noise" hand-wave on zero-tolerance gates.
- **R1.5 Installer surface:** installer updated to ship `flint-thinking.md` in the park case, and the promoted body of `flint.md` in the promote case. Rollback requires a new installer release (not just `git revert`) plus a documented local escape hatch.
- **R1.6 Per-task max_tokens:** current `evals/run_anthropic.py` only accepts one `--max-output-tokens` per invocation. Fixed by raising to 1024 uniformly for the fallback bench (deliverable-type tasks dominate). No runner change required.

---

## Project context (for the reviewer)

Flint is a prompt-level compression skill for Claude Code. System prompt forces every response into a compact symbolic IR: `@flint v0 hybrid` + `G:` (goal) `C:` (context) `P:` (plan) `V:` (verification) `A:` (action). On Claude Opus 4.7 with ~10k tokens of project-handbook cache_prefix:

| variant       | output tokens | latency | must_include |
| ------------- | ------------: | ------: | -----------: |
| verbose       | 736 ±28       | 15s ±1  | 86% ±1       |
| caveman       | 423 ±18       |  9s ±0  | 84% ±4       |
| flint (v0.3)  | 186 ±10       |  5s ±0  | 95% ±4       |

Corpus: 10 long-context coding tasks × 4 runs = 40 samples per cell. Bench driver: `scripts/run_stress_bench.sh`. Aggregator: `scripts/stress_table.py`. Runner: `evals/run_anthropic.py`. Must_include = substring match on committed technical stems; stemming intentional so structural formats can compete with prose.

Key internal APIs (observed from code):
- `src/flint/eval_common.py` defines transports: `plain`, `structured`, `sigil`, `schema-*`, `draft2schema-*`.
  - **`plain` → stored raw.** `direct_flint_stop_sequences` returns `[]` for non-`sigil` (line 194-200). `decode_variant_output` returns `output_text` as-is when `variant.transport != "sigil"` and not `schema-*` (line 248-252).
  - **`sigil` → stored NORMALIZED.** `materialize_direct_sigil` runs repair, normalize, synthesizes `[AUDIT]` (lines 203-238). Injects stop sequences (`[AUDIT]`, `Goal:`, `Constraints:`, `Hypothesis:`, `Plan:`) at gen time.
- `src/flint/parser.validate_document` only requires ≥1 clause (parser.py:291-299). Not sufficient for strict 5-slot gating.
- `evals/run_anthropic.py` accepts a single `--max-output-tokens` per run. Runner line 52 passes one value to the Anthropic API.
- `integrations/claude-code/install.sh` fetches `output-styles/flint.md` only (lines 48-56); re-running installer overwrites local `~/.claude/output-styles/flint.md` via `fetch` which uses `cp`/`curl -o` (line 38-46).

### The problem

Flint's contract is **structural**. Breaks hard outside task-shape workloads. User tried always-on; got burned on open-ended tasks. Caveman (`prompts/primitive_english.txt`) is **descriptive**, degrades gracefully.

Failure modes (`docs/failure_modes.md`): open-ended writing, conversational, summarization, ideation, long-form explanation, short-prompt no-context.

Artifacts referenced:
- `integrations/claude-code/flint_system_prompt.txt` (8-line strict default).
- `integrations/claude-code/output-styles/flint.md`.
- `integrations/claude-code/skills/{flint,flint-on,flint-off,flint-audit}/SKILL.md`.
- `integrations/claude-code/install.sh`.
- `prompts/primitive_english.txt`.
- `evals/tasks_stress_coding.jsonl`.

## Goal

Ship **Flint thinking mode**: prompt variant safe as always-on. Splits compression by **audience**:

- **Default user-facing** → Caveman-shape terse prose (same ruleset as `primitive_english.txt`).
- **Internal reasoning** → Flint IR.
- **Task output when user's question is IR-shape** (debug / review / refactor / architecture with crisp goal + verifiable endpoint) → Flint IR as user-visible answer.
- **Deliverables for humans** (RFC, PR description, docs, walkthrough, tutorial, essay, brainstorm, summary) → prose only.

Success = stress-bench win holds AND zero IR leak on pure-prose open-ended tasks AND correct classification on boundary subset.

## Non-goals

- Immediate replacement of v0.3.0 strict. Parallel variant first.
- Multi-turn context-accumulation bench.
- Slash command refactor beyond `flint-on` body (if promoted).
- Cross-model (Opus 4.7 only).
- Changing `src/flint/parser.validate_document` (scope-isolate: A4 uses bench-local strict check).

## The three refinements (baked in)

**R1 — Default prose is Caveman-shape.** Zone 1 encodes descriptive rules from `primitive_english.txt`: drop `the/a/an/is/are/be` where grammar allows, no filler, no intros, keep literals exact, one idea per line.

**R2 — Detection heuristic in the prompt.** Encode `docs/failure_modes.md` rule: "crisp technical goal + verifiable endpoint → IR; writing/chat/brainstorm/explanation/summarization → prose Caveman." Include disambiguation examples.

**R3 — Start without `<reasoning>` tags.** Anthropic API does not guarantee textual tags are hidden. Use implicit split. Add explicit tag only if bench shows leak.

## Deliverables

### Always produced

1. `integrations/claude-code/flint_thinking_system_prompt.txt` (~30-40 lines).
2. `integrations/claude-code/output-styles/flint-thinking.md`.
3. `evals/tasks_open_ended.jsonl` — 12 tasks: 8 pure-prose + 4 boundary. Fields: `must_include`, `format_check ∈ {prose, ir_ok}`, `expected_shape ∈ {prose, ir}`.
4. `scripts/run_stress_bench.sh` — add `flintthinking` cell (transport `plain`).
5. `scripts/stress_table.py` — add cell; add `ir_leak` + `strict_ir_pass` columns (raw content).
6. `scripts/run_fallback_bench.sh` — new harness.
7. `scripts/fallback_table.py` — new aggregator: `output`, `latency`, `must_inc`, `ir_leak`, `slot_leak`, `class_correct`.
8. `integrations/claude-code/install.sh` — fetch `output-styles/flint-thinking.md` additionally.

### If promote

9. `flint_system_prompt.txt` body swap.
10. `output-styles/flint.md` body swap.
11. Docs: README, methodology, architecture, failure_modes, faq.
12. `flint-on` skill body rewrite.
13. Launch posts reframe.
14. Version bump 0.3.0 → 0.4.0 (`pyproject.toml`, `src/flint/__init__.py`).
15. CHANGELOG, tag `v0.4.0`.
16. **Installer re-publish** on `main` raw URL. `curl | bash` path overwrites local `flint.md`.

### If park

17. `docs/flint_thinking_iteration_notes.md`.
18. `flint_thinking_system_prompt.txt` + `flint-thinking.md` stay; installer (#8) ships `flint-thinking.md` so users can opt in via `/config → Output style → flint-thinking`. `flint.md` unchanged. No version bump.

## Acceptance criteria (gate for promote)

All thresholds on **raw model output** (transport `plain`). 32 samples per fallback cell (8 prose × 4 runs); 40 on stress.

### Gate A — Task-shape corpus

- **A1:** `flintthinking` mean output tokens ≤ **220**.
- **A2:** mean latency ≤ **6s**.
- **A3:** must_include coverage ≥ **90%**.
- **A4 (v4, layout-independent):** ≥ **90%** of raw responses satisfy `strict_ir_pass`, defined as parser-plus-semantic test. No layout assumption — codebook blocks (`@cb[...]`) are allowed; the shipped `examples/debugging.flint` uses one and is a legitimate hybrid doc.

  Pseudocode:
  ```python
  REQUIRED_TAGS = {"G", "C", "P", "V", "A"}

  def strict_ir_pass(raw: str) -> bool:
      text = unicodedata.normalize("NFC", raw or "")
      # Parse — tolerate missing [AUDIT] (shipping prompt omits the audit by default).
      try:
          doc = parse_document(text)
      except FlintParseError:
          try:
              doc = parse_document(text.rstrip() + "\n\n[AUDIT]\n[placeholder]")
          except FlintParseError:
              return False
      if doc.header is None:
          return False
      if doc.header.version != "v0" or doc.header.mode != "hybrid":
          return False
      tags_present = {c.tag for c in doc.clauses}
      if not REQUIRED_TAGS.issubset(tags_present):
          return False
      return True
  ```

  Implemented standalone in `scripts/stress_table.py`. Uses `flint.parser.parse_document` + `flint.model.Document/Header` (public-ish package API). Not `flint validate` (shipped validator too permissive — parser.py:291-299 only requires ≥ 1 clause and the right mode-tag combo). The stricter contract here is intentional and documented as thinking-mode's shipping contract: exact `v0 hybrid` header + all five required clauses. Optional tags `{H, R, Q}` and optional `[AUDIT]` block remain allowed.

### Gate B — Pure-prose subset (8 tasks × 4 runs)

- **B1 — IR leak: zero tolerance.**
  ```python
  IR_PREFIX = re.compile(r"^\s*@flint\s+v\d+", re.IGNORECASE)
  leaked = lambda r: bool(IR_PREFIX.match(unicodedata.normalize("NFC", r["content"] or "")))
  ```
  Fail if any of 32 samples matches. Every leak must be eyeballed before iteration.

- **B2 — Token efficiency.** Mean ≤ **1.10 × caveman mean**. Tie-breaker within ±5%: `flintthinking` must_include ≥ caveman must_include.

- **B3 — Slot leak.** First 10 lines scanned for `^\s*[GCPVA]:\s`. ≤ 1 of 32 samples allowed (tolerates quoted code).

### Gate C — Boundary subset (4 tasks × 4 runs)

Per sample: `shape_detected = "ir"` if first non-ws line matches `^\s*@flint\s+v\d+` else `"prose"`. `class_correct = (shape_detected == expected_shape)`.

- **C1:** `class_correct` rate ≥ **75%** (12 of 16).
- **C2:** When `expected_shape == "ir"` and response is IR, `strict_ir_pass` holds (≤ 1 exploded of 8 allowed).
- **C3:** When `expected_shape == "prose"` and response is prose, no slot leak (≤ 1 of 8).

### Gate D — Exploded IR (cross-cutting)

Tokenize slot payload by `∧` + whitespace. "Exploded" = one slot ≥ 10 atoms while ≥ 2 others ≤ 2 atoms. ≤ 10% of all IR responses.

### Promote rule

Promote iff **A1-A4 AND B1-B3 AND C1-C3 AND D** all pass. Otherwise iterate up to 2 iterations, then park.

## Plan of execution

### Step 1 — Design the prompt (est. 1h)

Write `flint_thinking_system_prompt.txt`:

**Zone 1 — Caveman prose default (R1).** Verbatim semantic from `primitive_english.txt`.

**Zone 2 — internal reasoning (R3, implicit).** "When planning tool calls or interpreting observations, your reasoning can be structured as Flint IR. The user-visible response always follows the other zones." No `<reasoning>` tag in v1.

**Zone 3 — IR as user output (R2).** "If task has crisp technical goal AND verifiable endpoint (debug, review, refactor, architecture with explicit constraint), answer in Flint IR."

Disambiguation examples (≥ 4):
- "explain how TLS works" → prose.
- "explain this function and why test X fails" → IR.
- "brainstorm 5 names for Y" → prose.
- "review this PR, flag security issues" → IR.

**Zone 4 — deliverables.** RFC, PR description, docs, tutorials, essays, brainstorms, summaries, pure walkthroughs → prose only.

Smoke test before Step 2: 6 prompts (3 IR + 3 open-ended) via `run_anthropic.py` RUNS=1. Eyeball. Iterate. Log: `evals/runs/flint_thinking_smoke/`.

### Step 2 — Integrate into stress bench (est. 30min)

`scripts/run_stress_bench.sh`:
```bash
run_cell "flintthinking" "plain" "integrations/claude-code/flint_thinking_system_prompt.txt" "$i" 512 &
```

Transport `plain`: raw storage, no normalization, no stop sequences.

`scripts/stress_table.py`:
- Add `("Flint (thinking)", "stress_flintthinking")` to `CELLS`.
- Add `strict_ir_pass` + `ir_leak` columns computed on raw `content`.

Dry-run: `RUNS=1 ./scripts/run_stress_bench.sh`. 4 rows, new columns populated.

### Step 3 — Open-ended corpus (est. 1.5h)

`evals/tasks_open_ended.jsonl` — 12 tasks. Schema: existing fields + `expected_shape ∈ {"ir", "prose"}`.

**Subset 1: 8 pure-prose (Gate B)**

| id | failure mode | expected_shape |
| --- | --- | --- |
| explain-gc-generational | long-form explanation | prose |
| brainstorm-pubsub-latency | creative ideation | prose |
| rfc-user-schema-change | open-ended writing | prose |
| walkthrough-parser | long-form explanation | prose |
| opinion-design-choice | back-and-forth | prose |
| tutorial-prompt-cache | open-ended writing | prose |
| summarize-paper-snippet | summarization | prose |
| short-opinion-chat | short-prompt no-context | prose |

**Subset 2: 4 boundary (Gate C) — v4 refinement per Codex R3.2**

Codex R3 correctly noted that v3's `feedback-on-code-quality` (attached code → review) and `sanity-check-mutex-approach` (scoped architecture choice) both resolve as IR under the product's own rule — `README.md:104` and `integrations/claude-code/skills/flint/SKILL.md:7` explicitly market Flint for "review this diff" and "sketch this architecture" asks. v4 replaces both with tasks whose body **explicitly disavows a verifiable endpoint** ("non cerco una decisione", "non serve un fix"). That disavowal is what makes the rule resolve to prose even when concrete tech content is present.

| id | expected_shape | prompt gist | cue conflict |
| --- | --- | --- | --- |
| debug-and-explain-function | ir | "Ecco `auth.py`. Spiegami cosa fa e perché `test_expiry` fallisce." | Surface = "spiegami" (prose cue); endpoint = concrete test failing (verifiable). Rule → IR. |
| review-small-diff | ir | "Cosa ne pensi di questo diff (8 righe)? È sicuro in produzione?" | Surface = "cosa ne pensi" (conversational cue); endpoint = diff + safety decision (verifiable). Rule → IR. |
| retro-narrative-redis-outage | prose | "Ti racconto l'outage di ieri: Redis saturato alle 3am, failover parziale. Non serve un fix — voglio capire come la vedi tu, che morale traiamo." | Surface = concrete tech incident (IR cue); endpoint = *explicitly disavowed* ("non serve un fix"), ask = narrative lesson. Rule → prose. |
| tradeoff-discussion-narrative | prose | "Microservices vs monolito per un team di 3 full-stack. Non cerco una decisione, voglio capire come ragioni sui tradeoff — filosofia più che raccomandazione." | Surface = architecture framing (IR cue, per README skill claim); endpoint = *explicitly disavowed* ("non cerco una decisione"), ask = reasoning-style narrative. Rule → prose. |

Balanced 2 IR : 2 prose. Each task has `must_include` stems hand-chosen. Crucially, the prose-side tasks now contain an explicit "non cerco X verificabile" clause — this is the signal the thinking-mode prompt's heuristic must detect to override the concrete-tech surface cue. The Gate C1 75% bar on 16 samples (12 of 16) now actually tests the routing boundary the product cares about: does the model respect the user's explicit framing when it conflicts with task-shape cues?

`max_tokens = 1024` uniform (runner doesn't support per-task; line 52 passes single value). Accept the waste on short chat tasks.

### Step 4 — Fallback harness (est. 45min)

`scripts/run_fallback_bench.sh` based on `run_stress_bench.sh`.
- `TASKS="evals/tasks_open_ended.jsonl"`, `OUT_DIR="evals/runs/fallback"`.
- 4 cells: `verbose`, `caveman`, `flintstrict`, `flintthinking`. **All `plain` transport** (fallback is about raw leak detection).
- `flintstrict` = `flint_system_prompt.txt` under `plain`. Expected to fail open-ended — that's the numeric contrast for launch.
- `max_tokens=1024` uniform.

`scripts/fallback_table.py`:
```python
import re, unicodedata

IR_PREFIX = re.compile(r"^\s*@flint\s+v\d+", re.IGNORECASE)
SLOT_HEADER = re.compile(r"^\s*[GCPVA]:\s", re.MULTILINE)

def nfc(s): return unicodedata.normalize("NFC", s or "")

def ir_leak_rate(rows):
    return sum(1 for r in rows if IR_PREFIX.match(nfc(r["content"]))) / max(1, len(rows))

def slot_leak_rate(rows):
    hits = 0
    for r in rows:
        head = "\n".join(nfc(r["content"]).splitlines()[:10])
        if SLOT_HEADER.search(head): hits += 1
    return hits / max(1, len(rows))

def class_correct_rate(rows, tasks_by_id):
    hits = total = 0
    for r in rows:
        expected = tasks_by_id[str(r["task_id"])].get("expected_shape")
        if expected is None: continue
        total += 1
        detected = "ir" if IR_PREFIX.match(nfc(r["content"])) else "prose"
        if detected == expected: hits += 1
    return hits / max(1, total)
```

Columns: `variant`, `n`, `output`, `latency`, `must_inc`, `ir_leak`, `slot_leak`, `class_correct`. Gate D `exploded_ir` in stress table (shared helper).

### Step 5 — Run benches (est. 30min wall-clock, ~$5)

```bash
RUNS=4 ./scripts/run_stress_bench.sh && python3 scripts/stress_table.py
RUNS=4 ./scripts/run_fallback_bench.sh && python3 scripts/fallback_table.py
```

### Step 6 — Analyze and decide

**Iteration loop (budget: 2):**

1. Identify failing gate(s). Eyeball failing samples.
2. Edit prompt based on pattern.
3. Smoke re-run (RUNS=1) on BOTH benches (~$1.25). Unlimited smoke tries within the iteration.
4. Once smoke looks green, commit prompt, spend iteration budget on full RUNS=4 re-run of BOTH benches.
5. Re-apply gates. Green → Step 7 promote. Red → iteration 2.

**Hard rule:** shipped prompt must have one full clean RUNS=4 pass on both corpora.

If iteration 2 full still red → Step 7 park.

Failure → action map:

| failing gate | action |
| --- | --- |
| A1-A3 | Strengthen R2 IR-trigger examples |
| A4 strict_ir_pass | Add anti-pattern: "never cram all atoms into A:" |
| B1 IR leak | Strengthen R2 prose-trigger examples |
| B2 tokens | Tighten Zone 1 Caveman rules |
| B3 slot leak (blended) | Add contrastive example: "this is prose / this is IR / never mix" |
| C1 classification | Add one more boundary disambiguation pair |
| D exploded | Add slot-atom-count guidance |

### Step 7 — Ship or park

**Promote:**
1. `cp flint_thinking_system_prompt.txt flint_system_prompt.txt`.
2. Swap `output-styles/flint.md` body.
3. Confirm `install.sh` still fetches `flint.md` at the raw URL.
4. Docs, skill body rewrite, launch posts, version bump, changelog, tag.
5. Push main + tag. New commit (never amend).
6. **Rollback readiness note** in CHANGELOG: "re-run installer at tag `v0.3.0` OR `/flint-on` in-session."

**Park:**
1. Keep prompt files in repo.
2. **Update `install.sh`** to also fetch `flint-thinking.md` (Deliverable #8).
3. Write iteration notes.
4. Commit. No version bump, no tag.

## Rollback

### Pre-promote
Nothing to roll back.

### Post-promote (v1 fix from Codex R1.5)

`git revert` alone insufficient — installer writes to users' local `~/.claude/output-styles/flint.md`.

1. **Repo revert:** `git revert <promote-commit>; git push origin main`. Restores v0.3 body at HEAD.
2. **Installer release:** re-running `curl | bash` fetches `main`'s `flint.md` (cp overwrite or `curl -o` overwrite, line 38-46 of `install.sh`). Users re-run, local copy reverted.
3. **In-session escape:** `/flint-on` forces strict IR without re-install. Documented in CHANGELOG.
4. **Communication:** announce on the same channel as launch post.

**No feature flag:** output-style is a static body; runtime toggling would require runtime prompt swap. `/flint-on` IS the runtime escape.

**Exposure window:** time between user promote-install and rollback-install. Mitigated by 24h observation before launch announcement.

## Open decisions (Step 1)

1. Keep `@flint v0 hybrid` header in thinking-mode IR? **Yes.** Parsers depend on it. 4 tokens = noise.
2. Version: 0.4.0 vs 1.0.0? **0.4.0.** 1.0.0 implies grammar stability not yet committed.
3. Changelog framing? **Behavioural default shift.** Users with explicit `outputStyle: "flint"` get new body on re-install; `flint-on` restores prior semantic.

## Risks and mitigations

| risk | mitigation |
| --- | --- |
| Blended Caveman+Flint output | Gates B3 + D. Codex v1 top risk, both gates added. |
| Heuristic misclassification | Gate C direct; iteration adds disambiguation pairs. |
| A1 output token regression | Prompt grew 8 → ~30-40 lines. A1 slack 34 tok. If exceeded, compress prompt by removing examples. |
| IR leaks despite R3 | Iteration 2 tries explicit `<reasoning>` tag. Verify Claude Code hides it. |
| Normalized-not-raw grading | Fixed v2: all fallback cells `plain` transport. A4 bench-local. `sigil` avoided. |
| Permissive validator for A4 | Fixed v2: A4 independent of `flint validate`. |
| Rollback doesn't reach users | Fixed v2: new installer release + `/flint-on` escape. |
| Short-prompt loses tokens to Caveman | Expected. B2 1.10× tolerance designed for this. |
| Park users can't opt in | Fixed v2: installer ships `flint-thinking.md` (#8). |

## Time and cost

Design + bench: 5-7h. API:
- Initial RUNS=4 both: ~$5.
- Each smoke RUNS=1: ~$1.25.
- Iteration budget: up to 2 × (smoke + full) = ~$15 worst, ~$7-10 realistic.

## Acceptance signal

- Promote: both benches green, v0.4.0 tagged, installer re-publishable, `git status` clean, pytest 73/73 green.
- Park: iteration notes + experimental prompt + installer update committed. No tag. `git status` clean.
