# Flint

**Compress the work, not just the words.**

Flint is a proposed **reasoning IR** (_intermediate representation_) for LLMs.  
It is **not** another funny output dialect.

The thesis is simple:

> Most current "compression skills" reduce the size of the visible answer.  
> Flint tries to reduce **reasoning overhead**, **context overhead**, and **expansion overhead** by compiling a task into a compact symbolic draft, expanding only uncertain nodes, and always keeping a short human-auditable view.

In one line:

> **Caveman is speech compression. Flint is reasoning compilation.**

---

## Why this exists

Many current techniques save tokens by making the final answer shorter. That is useful, but limited.

If the model still:
- loads the same verbose memory every session,
- reasons in a long natural-language chain,
- expands every step whether needed or not,

then you have mostly compressed the **mouth**, not the **mind**.

Flint is designed around a stronger question:

> Can we give LLMs a compact, structured, model-friendly language for *working* on the task, while still producing a human-readable answer when needed?

That question is scientifically plausible for three reasons:

1. **Symbolic compression already works** when the symbols are familiar to the model rather than invented from scratch.
2. **Concise intermediate reasoning can preserve quality** while cutting reasoning budget substantially.
3. **Reasoning and visible output are already treated as separate channels** by modern APIs.

Flint is the bridge between those facts.

---

## What Flint is

Flint is a **5-layer skill/runtime design**:

1. **Adaptive codebook**  
   Repeated entities and constraints become short local symbols.

2. **Symbolic draft reasoning**  
   The model writes a compact task draft instead of a long prose chain-of-thought.

3. **Selective expansion**  
   Only uncertain, risky, or precision-critical nodes get expanded.

4. **Audit decoder**  
   The system can always emit a short normal-language explanation.

5. **Latent-ready backend**  
   On open-weight models, symbolic nodes can later be mapped to learned discrete or latent reasoning tokens.

This makes Flint useful in two modes:

- **Prompt-only mode** for closed models and commercial APIs.
- **Research mode** for open models, where the IR can become a true learned backend.

---

## Design principles

### 1. Never invent a random alien language
A totally arbitrary machine-language usually fails because the model has not learned stable semantics for it.

Flint therefore prefers:
- mathematical operators the model likely already knows,
- short structured tags,
- local project-specific aliases,
- optional ASCII-safe fallbacks.

### 2. Keep the draft compact, not cryptic
Compression is only useful if the model can still operate on it reliably.

Flint drafts should be:
- short,
- typed,
- easy to expand,
- easy to verify.

### 3. Expand only where it pays
The default should be:
- short draft first,
- verify confidence,
- expand only uncertain or high-risk branches.

### 4. Always keep an audit path
Any serious system needs a human-readable explanation path.

Flint therefore always supports:
- `draft` view,
- `audit` view,
- `hybrid` view.

### 5. Separate task classes
Not all tasks benefit equally from compression.

Flint is strongest for:
- coding,
- debugging,
- planning,
- long-context memory,
- architecture review,
- repetitive agent workflows.

Flint should be conservative for:
- arithmetic detail,
- legal/compliance edge cases,
- safety-critical medical reasoning,
- formal proofs unless explicit verification is added.

---

## How it works

## Layer 1 — Adaptive codebook

Repeated concepts get local aliases.

Example:

```flint
@cb[
  μ1=auth.middleware;
  μ2=jwt.refresh;
  κ1=backcompat;
  κ2=security;
  ρ1=clock_skew;
  τ1=401_loop
]
```

Why this matters:
- repeated long identifiers collapse into very short tokens,
- the model reuses the same symbolic handles across the session,
- session memory can be stored as small "capsules" instead of prose blobs.

This is not a universal dictionary.  
It is a **local codebook**, built around the current repo/problem/session.

---

## Layer 2 — Symbolic draft reasoning

Instead of a long chain like:

> "First I will inspect the middleware, then I will compare expiry handling, then I will consider backward compatibility..."

Flint prefers:

```flint
G: fix(μ1)
C: κ1 ∧ κ2
H: cmp(expiry,<) ⇒ τ1
P: inspect(expiry_calc) → Δ(<=) → test(edge_expiry,ρ1)
V: unit ∧ integration
Q: refresh_rotation ?
```

This is the core move:
- **G** = goal
- **C** = constraints
- **H** = hypothesis
- **P** = plan
- **V** = verification
- **Q** = open question

That draft is short, typed, and still actionable.

---

## Layer 3 — Selective expansion

Not every node deserves prose.

Flint expansion policy:

1. Produce draft.
2. Score uncertainty/risk.
3. Expand only:
   - `?` uncertain nodes,
   - `!` high-risk nodes,
   - exact-calculation nodes,
   - user-requested detailed explanations.
4. Stop when marginal value drops.

This is the key difference from "always verbose CoT".

---

## Layer 4 — Audit decoder

Every draft can be decoded into short human language.

Example:

### Draft

```flint
G: fix(μ1)
C: κ1 ∧ κ2
H: cmp(expiry,<) ⇒ τ1
P: inspect(expiry_calc) → Δ(<=) → test(edge_expiry,ρ1)
V: unit ∧ integration
```

### Audit

```text
Likely bug in auth middleware expiry comparison.
Preserve backward compatibility and security.
Check whether the expiry comparison uses < instead of <=.
If confirmed, patch the comparison and test edge-expiry and clock-skew cases.
Verify with unit and integration tests.
```

The user sees the audit view.  
The runtime may use the draft view.

---

## Layer 5 — Latent-ready backend

Prompt-only Flint already works as a skill.

But the deeper version is a research track:
- replace some symbolic nodes with learned discrete tokens,
- optionally pair Flint with tokenizer adaptation,
- optionally map high-frequency patterns into latent or compressed reasoning states.

That is the path from:
- **syntax trick**
to
- **real reasoning infrastructure**.

---

## Modes

Flint supports 5 operating modes.

### `draft`
Output only the compact IR.

Use when:
- tool chains consume the output,
- the user wants maximum density,
- the task is repetitive and already familiar.

### `audit`
Return normal-language output only.

Use when:
- the user wants readability,
- the task is sensitive,
- the audience is human-first.

### `hybrid`
Return IR + short audit note.

Use when:
- debugging,
- agent orchestration,
- collaborative coding,
- benchmark runs.

### `memory`
Store/update compact session capsules.

Use for:
- project memory,
- persistent repo rules,
- recurring constraints,
- task handoffs.

### `compile`
Turn a user request into:
- codebook,
- draft,
- expansion plan,
- execution checklist.

This is the most "agentic" mode.

---

## Grammar

Below is a minimal GitHub-ready grammar.

## Unicode form

```ebnf
program    ::= header? codebook? clause+
header     ::= "@flint" version mode?
version    ::= "v0"
mode       ::= "draft" | "audit" | "hybrid" | "memory" | "compile"

codebook   ::= "@cb[" binding (";" binding)* "]"
binding    ::= symbol "=" value

clause     ::= tag ":" expr
tag        ::= "G" | "C" | "H" | "P" | "V" | "R" | "Q" | "M" | "A"

expr       ::= term (op term)*
term       ::= atom
             | func
             | group

func       ::= ident "(" args? ")"
args       ::= expr ("," expr)*
group      ::= "(" expr ")"

atom       ::= symbol | ident | number | quoted

op         ::= "∧" | "∨" | "⇒" | "→" | "≈" | "⊥" | "Δ" | "?" | "!"
```

## ASCII-safe fallback

```ebnf
AND   = &
OR    = |
IMPL  = =>
THEN  = ->
DELTA = delta(...)
CONFLICT = FAIL
UNCERTAIN = ?
RISK = !
```

---

## Clause semantics

| Tag | Meaning | Example |
|---|---|---|
| `G` | Goal | `G: fix(μ1)` |
| `C` | Constraints | `C: κ1 ∧ κ2` |
| `H` | Hypothesis | `H: cache_stale ⇒ mismatch` |
| `P` | Plan / next actions | `P: inspect(x) → patch(y)` |
| `V` | Verification | `V: unit ∧ integration` |
| `R` | Risks | `R: ! regression(auth)` |
| `Q` | Open questions | `Q: env_specific ?` |
| `M` | Memory capsule | `M: pref(short_audit)` |
| `A` | Final answer stub | `A: explain(patch)` |

---

## Operators

| Operator | Meaning |
|---|---|
| `∧` | both / conjunction |
| `∨` | either / disjunction |
| `⇒` | implies / likely cause |
| `→` | ordered next step |
| `Δ` | patch / change / diff |
| `≈` | approximate / similar |
| `⊥` | contradiction / failure |
| `?` | uncertainty |
| `!` | high risk / priority |

---

## Example 1 — Debugging

### User
> Review this auth middleware bug and suggest the minimal fix.

### Flint draft

```flint
@flint v0 hybrid
@cb[
  μ1=auth.middleware;
  κ1=backcompat;
  κ2=security;
  ρ1=clock_skew;
  τ1=401_loop
]

G: fix(μ1)
C: κ1 ∧ κ2
H: cmp(expiry,<) ⇒ τ1
P: inspect(expiry_calc) → Δ(<=) → test(edge_expiry,ρ1)
V: unit ∧ integration
R: ! session_regression
Q: refresh_rotation ?
A: minimal patch + test note
```

### Audit view

```text
Most likely issue: the middleware treats edge-expiry incorrectly.
Keep backward compatibility and security guarantees.
Check whether expiry uses < where <= is required.
If confirmed, apply the minimal patch and test edge-expiry plus clock-skew.
Watch for session-regression risk.
```

---

## Example 2 — Architecture choice

### User
> Microservices or monolith for a 6-person team shipping in 4 months?

### Flint draft

```flint
@flint v0 hybrid

G: choose(arch)
C: team(6) ∧ deadline(4m) ∧ ship_fast
H: low_ops_capacity ⇒ prefer(monolith)
P: compare(dev_speed, deploy_complexity, fault_isolation, future_split)
V: score(time_to_first_release, operability, migration_cost)
R: ! premature_distribution
A: recommend(default=modular_monolith)
```

### Audit view

```text
Default recommendation: modular monolith.
Reason: small team, short deadline, and likely limited ops capacity.
Compare release speed, deployment complexity, fault isolation, and future extraction cost.
Biggest risk is premature distribution.
```

---

## Example 3 — Memory compression

### Original project memory

```text
The API must remain backward compatible with v2 clients.
Do not rename the public auth endpoints.
We prefer minimal diffs.
Always add tests for boundary conditions around expiry and cache invalidation.
```

### Flint memory capsule

```flint
@flint v0 memory
M: compat(v2_clients) ∧ keep(public_auth_endpoints)
M: pref(minimal_diff)
M: test(boundary_expiry) ∧ test(cache_invalidation)
```

This is where Flint becomes more than a style:
it compresses **persistent working context**.

---

## What makes Flint different from Caveman

Caveman is a strong reference point because it proves that aggressive surface compression is useful in practice. Its README reports an average reduction from 1214 to 294 output tokens across benchmark prompts, or about 65% savings, while explicitly noting that reasoning tokens are untouched. That makes it an output-compression skill, not yet a full reasoning-compression stack.

Flint differs in three ways:

1. **It compresses task structure, not just prose.**
2. **It is built to decide what not to expand.**
3. **It is explicitly designed for a future learned backend.**

So the upgrade path is:

```text
plain prose
→ terse prose
→ symbolic draft
→ selective expansion
→ symbolic/latent hybrid
```

---

## Minimal system prompt

Use this as a first prompt-only implementation.

```text
You are Flint, a reasoning compiler for LLM workflows.

Goal:
Maximize information density while preserving correctness, actionability, and auditability.

Operating rules:
1. Do not default to long prose reasoning.
2. First compile the task into a compact typed draft using Flint clauses.
3. Use a local codebook for repeated entities, files, modules, constraints, risks, and preferences.
4. Expand only nodes that are uncertain (?), high-risk (!), precision-critical, or explicitly requested by the user.
5. Keep the draft semantically transparent: prefer familiar mathematical/symbolic operators over invented opaque codes.
6. Always be able to emit a short human-readable audit summary.
7. If the task is arithmetic-, legal-, medical-, or safety-critical, increase explicitness and verification.
8. If confidence is high and the task is routine, stop early after a concise draft and short audit.
9. Preserve code, paths, commands, schema names, APIs, versions, and exact literals verbatim.
10. Never hide uncertainty. Mark it with Q:, ?, R:, or !.

Output contract by mode:

Mode=draft:
- Return only:
  @flint ...
  @cb[...] (optional)
  clauses

Mode=audit:
- Return only a short natural-language summary.

Mode=hybrid:
- Return:
  1) Flint draft
  2) a short audit block

Mode=memory:
- Return only compact M: clauses suitable for storage.

Mode=compile:
- Return:
  1) codebook
  2) draft
  3) expansion targets
  4) verification checklist

Clause tags:
G goal
C constraints
H hypothesis
P plan
V verification
R risks
Q open questions
M memory
A answer stub

Operators:
∧, ∨, ⇒, →, Δ, ≈, ⊥, ?, !

Default behavior:
- Prefer 4–8 clauses.
- Prefer short symbols for repeated entities.
- Prefer one-line audit summaries unless detail is necessary.
```

---

## Runtime policy

A practical host loop for Flint:

```python
def sigil_run(task, mode="hybrid"):
    ctx = load_memory_capsules()
    cb = build_local_codebook(task, ctx)
    draft = compile_to_sigil(task, cb, ctx)

    risk = estimate_risk(draft)
    uncertainty = estimate_uncertainty(draft)

    if mode == "draft":
        return draft

    if mode == "memory":
        return compress_memory(task, cb)

    if risk == "low" and uncertainty == "low":
        return hybrid(draft, short_audit(draft))

    expansion_targets = pick_targets(draft, risk, uncertainty)
    expanded = expand_only(draft, targets=expansion_targets)

    if mode == "audit":
        return short_audit(expanded)

    return hybrid(expanded, short_audit(expanded))
```

The important part is not the exact code.
The important part is the policy:

> **compile first, expand second, explain last**

---

## Suggested repo structure

```text
flint/
├─ README.md
├─ LICENSE
├─ prompts/
│  ├─ system.txt
│  ├─ compiler.txt
│  └─ audit.txt
├─ grammar/
│  ├─ flint.ebnf
│  └─ sigil_ascii.md
├─ examples/
│  ├─ debugging.md
│  ├─ planning.md
│  ├─ architecture.md
│  └─ memory_capsules.md
├─ evals/
│  ├─ tasks.jsonl
│  ├─ run_openai.py
│  ├─ run_anthropic.py
│  ├─ run_gemini.py
│  ├─ metrics.py
│  └─ report.ipynb
└─ docs/
   ├─ design.md
   ├─ research-notes.md
   └─ roadmap.md
```

---

## Benchmark plan

This is the most important part if the project is meant to be taken seriously.

## Baselines

Compare against:

1. **Verbose baseline**  
   Normal assistant output.

2. **Terse baseline**  
   Same assistant, instructed to be concise.

3. **Caveman-style baseline**  
   Strong surface-compression baseline.

4. **Flint draft-only**

5. **Flint hybrid**

6. **Flint + adaptive reasoning budget**  
   Where the API supports it.

Do **not** compare only against verbose output.  
That would overstate the benefit.

---

## Task categories

Use the same categories that matter in real agent workflows:

- bug explanation,
- bug fixing,
- refactoring,
- architecture choice,
- code review,
- database/debugging tasks,
- long-context memory reload,
- multi-step planning,
- tool-using agent loops.

Add two stress categories:

- **precision tasks**  
  where compression may hurt,
- **memory tasks**  
  where persistent capsules should help.

---

## Metrics

### Quality
- task success / exact correctness
- pass@k where relevant
- human preference
- verifier pass rate
- regression rate

### Efficiency
- input tokens
- output tokens
- total billed tokens
- reasoning-budget tokens where exposed by API
- latency
- memory loaded per session

### Compression behavior
- clause count
- expansion rate
- codebook reuse rate
- audit length
- percent of tasks resolved without expansion

### Reliability
- contradiction rate (`⊥`)
- hidden assumption rate
- audit-vs-draft mismatch rate
- failure recovery rate

---

## Benchmark hypotheses

These are **targets**, not claims.

### H1 — Surface efficiency
Flint hybrid should beat normal verbose answers clearly on output-token count.

### H2 — Structural efficiency
Flint should also beat a generic "be concise" baseline on repeated workflows because codebooks and memory capsules remove repeated boilerplate.

### H3 — Total efficiency
On tasks where early stopping works, Flint + adaptive budgeting should reduce total billed tokens, not just visible output.

### H4 — Accuracy retention
On coding/planning/review tasks, Flint hybrid should stay within a small quality delta of verbose baselines.

### H5 — Failure locality
When Flint fails, it should fail in a localized clause that can be expanded, not in a long opaque wall of text.

---

## Ablations

Run these ablations or the project will look hand-wavy.

1. **No codebook**  
   Same grammar, no local aliases.

2. **No selective expansion**  
   Always expand every clause.

3. **No audit decoder**  
   Draft only.

4. **ASCII only vs Unicode operators**

5. **Memory capsules on vs off**

6. **Adaptive reasoning budget on vs off**

7. **Open-weight symbolic-only vs symbolic+learned tokens**  
   research mode only.

---

## Failure modes

Flint is promising, but not magic.

### 1. Overcompression
The draft becomes too short to preserve important distinctions.

Mitigation:
- force expansion for critical clauses,
- keep exact literals untouched,
- add verifier checks.

### 2. Symbol drift
A local alias starts meaning slightly different things across turns.

Mitigation:
- freeze codebook entries once established,
- version memory capsules,
- decode periodically into audit text.

### 3. False confidence
The system stops early even though the task needed deeper reasoning.

Mitigation:
- expand on safety-critical categories,
- use verifier or self-check passes,
- allow user-forced `detail` mode.

### 4. Precision damage
Compact symbolic summaries can hurt arithmetic or exact formal work.

Mitigation:
- mark such tasks as precision-critical,
- switch to explicit derivation mode,
- reserve compression for structure, not calculation.

### 5. Poor model fit
Some models may dislike certain symbols or parse them inconsistently.

Mitigation:
- keep an ASCII-safe fallback,
- benchmark per model,
- learn model-specific operator subsets.

---

## Research roadmap

## Phase 1 — Prompt-only Flint
- ship grammar,
- ship system prompt,
- add examples,
- run three-way evals,
- measure token and quality trade-offs.

## Phase 2 — Stateful Flint
- persistent codebooks,
- memory capsules,
- expansion policy,
- per-project optimization.

## Phase 3 — Learned Flint
- add special tokens or compressed nodes,
- pair with tokenizer adaptation,
- train a symbolic/latent translator,
- keep audit decoder for human visibility.

## Phase 4 — Agent-native Flint
- tool-aware clauses,
- planner/executor split,
- verifier-guided early exit,
- auto-compilation of project memory.

---

## Scientific basis

Flint is aligned with several strands of current research:

- **Caveman** shows that strong output compression is already useful in practice, but also states clearly that reasoning tokens remain untouched.
- **MetaGlyph** suggests that symbolic compression works best when it uses symbols models already understand rather than an invented opaque code.
- **Chain of Draft** and **Draft-Thinking** support the idea that concise intermediate reasoning can preserve much of the benefit of long CoT with far fewer tokens.
- **COCONUT** supports the larger thesis that language is not the only valid medium for reasoning, and that latent reasoning can outperform text CoT on some search-heavy tasks.
- **ReTok** supports the idea that tokenizer design is not a detail; it is part of the efficiency stack.
- **OpenAI**, **Anthropic**, and **Gemini** all now expose explicit controls or artifacts for reasoning/thinking behavior, which makes a budget-aware skill architecture immediately practical.

---

## Honest status

What is real today:
- the prompt-only version,
- the grammar,
- the codebook,
- the audit pattern,
- adaptive-budget orchestration,
- benchmarking.

What is research-grade but plausible:
- learned symbolic nodes,
- discrete compressed reasoning tokens,
- latent backends paired with Flint clauses.

What is **not** yet proven:
- that one universal compact language will dominate across models,
- that aggressive compression always reduces total cost,
- that latent reasoning is always better than explicit reasoning.

This project should be sold as:
- **ambitious but falsifiable**,
not
- magical.

---

## One-sentence pitch

> **Flint is a reasoning compiler for LLMs: it turns verbose natural-language work into a compact symbolic draft, expands only uncertain parts, and always keeps a human-readable audit trail.**

---

## References

- Caveman — https://github.com/JuliusBrussee/caveman
- OpenAI Reasoning Models Guide — https://developers.openai.com/api/docs/guides/reasoning
- Anthropic Extended Thinking — https://platform.claude.com/docs/en/build-with-claude/extended-thinking
- Gemini Thinking — https://ai.google.dev/gemini-api/docs/thinking
- Gemini Pricing — https://ai.google.dev/gemini-api/docs/pricing
- MetaGlyph — https://arxiv.org/abs/2601.07354
- Chain of Draft — https://arxiv.org/abs/2502.18600
- Draft-Thinking — https://arxiv.org/abs/2603.00578
- COCONUT — https://arxiv.org/abs/2412.06769
- ReTok — https://arxiv.org/abs/2410.04335
- Reasoning Models Know When They're Right — https://arxiv.org/abs/2504.05419
