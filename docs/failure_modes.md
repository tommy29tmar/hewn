# Failure modes

Where Flint breaks, what the breakage looks like, and what you can do about
it. This doc is the companion to the README's "Honest scope" section —
written for people who want to use Flint in production and need to know
what they're signing up for.

## Tasks Flint is not for

Flint's structural contract assumes the answer *has* a G/C/P/V/A shape. Many
tasks don't. In order of bluntness:

- **Open-ended writing.** "Write me a blog post about X." Flint will
  produce a 6-line skeleton, which is not what you asked for.
- **Conversational back-and-forth.** "What do you think?" There's nothing
  to fill the Plan slot with.
- **Pure summarization.** "Summarize this paper." The audit slot exists for
  prose, but you're better off just asking Claude normally — you're paying
  for the Flint prompt without benefiting from the IR.
- **Creative ideation.** "Brainstorm 20 names for my startup." Flint forces
  structure where divergent thinking wants the opposite.
- **Long-form explanation.** "Explain how TLS works." Flint will give you
  the atoms, but you wanted the prose.

**Rule of thumb:** if the task has a crisp technical goal and a verifiable
endpoint, Flint fits. If the task is "think out loud with me", turn Flint
off — pick `default` in `/config → Output style`, or remove the
`outputStyle` field from your settings.

## Drift patterns

The model sometimes drifts off the IR contract. The normalizer catches the
common cases; these are the ones you'll see.

### 1. Whitespace and casing drift (repairable, common)

```
@FLINT V0 HYBRID
g: fix_auth
c : trust_boundary  ∧   "X-Forwarded-For"
```

`flint-ir repair` fixes this silently. No action needed, but `flint-ir audit
--explain` will show the normalization.

### 2. Unicode operator drift (repairable)

The model emits `&` instead of `∧`, or `->` instead of `→`. The normalizer
swaps them using the table in [`grammar/flint_ascii.md`](../grammar/flint_ascii.md).
Also fine.

### 3. Missing slot (schema error)

```
@flint v0 hybrid
G: fix_auth
C: trust_boundary ∧ "X-Forwarded-For"
P: drop_header ∧ bind(req.ip)
A: ! header_spoof
```

No `V:` slot. The parser returns `schema_error: missing verification clause`.
The shipped skill rarely does this on Opus 4.7 (< 2% of 40 samples in the
stress bench), but it happens. The drop-in move is to call Claude again with
the same prompt — Flint's determinism comes from the system prompt being
small and load-bearing, so retry variance is low.

### 4. Prose leak (content error)

```
@flint v0 hybrid
G: fix_auth
Here's a breakdown of the fix:
C: trust_boundary ∧ "X-Forwarded-For"
...
```

The model tries to be helpful and adds a sentence. The normalizer strips
leading "Here's a breakdown:" / "Certainly!" / "Let me think about this."
preambles. Anything the normalizer can't pattern-match becomes a
`content_error`.

### 5. Anchor miss (silent failure)

The model writes the right idea with a different atom:

```
V: check(ip_binding)      # Correct but the must_include stem expected `bind`
```

This is the failure mode you should actually worry about. It won't trip the
parser or the verifier unless you passed explicit `--anchor` arguments. On
the stress bench the must_include stemmer catches most of these
(`bind` matches both `bind(req.ip)` and `ip_binding`), but on your own
data the stems are yours to choose.

If you need hard anchor checking, use:

```bash
flint-ir audit --explain response.flint --anchor "X-Forwarded-For" --anchor 401
```

The verifier will fail loudly if either anchor is missing.

## Prompt/model combinations that misbehave

### Short prompts with no context

On tasks under ~300 input tokens with no `cache_prefix`, Flint's output is
similar in size to a plain "be concise" baseline, because there isn't enough
work to compress. Flint's edge kicks in when the context is meaty (agent
loops, RAG, loaded CLAUDE.md). For one-shot Q&A with short prompts, you're
paying ~90 tokens of Flint system prompt for marginal output savings.

**If your usage is one-shot short Q&A, Flint is probably not worth it.**
The README's numbers come from long-context usage because that's the shape
that matters for Claude Code / agent loops / RAG.

### Models other than Opus 4.7

The shipped prompt was tuned on Opus 4.7. Earlier data (pre-cleanup) showed
Flint still winning on Sonnet 4.6 (-24% tokens, -52% latency, +8pt concept
coverage) and on Opus 4.6 (-47% tokens, -68% latency, -6pt concept
coverage — the only cell where Flint lost on coverage). Sonnet 4 posted
modest token gains (-3%) but large latency gains (-44%) and a big coverage
improvement.

If you're on a different model, the bench runs in 5 minutes — try it and
open a PR with your numbers.

### Non-Anthropic providers

Flint is provider-agnostic in principle but has only been validated on the
Anthropic Messages API. The prompt cache behavior is Anthropic-specific;
OpenAI and Google have different cache semantics that the `eff_total`
column in `stress_table.py` doesn't model correctly.

**Rule of thumb:** Flint will work on any frontier LLM that respects a
system prompt; the *exact* numbers won't transfer. Treat claims outside
Opus 4.7 + Anthropic as untested until you run the bench yourself.

## What `flint-ir audit --explain` tells you

Pipe any suspicious response through it. You get:

```
==> INPUT
(raw response as received)

==> NORMALIZED
(post-normalize.py — whitespace, case, unicode, preamble strip)

==> PARSED
(syntax tree — slots, atoms, operators)

==> VERIFICATION
(schema OK / error)
(anchors matched / missed)
(drift detected / none)

==> RENDERED
(prose rerender of the parsed tree — what a human would read)
```

If you're debugging a bad answer, this is the one tool you need. It shows
exactly where the failure happened in the pipeline so you know whether to
retry, adjust the prompt, or eat the loss.

## When to disable Flint mid-session

If you're chatting with Claude Code and you hit a question Flint is
obviously bad at (explanation-heavy, creative, back-and-forth), you have
three ways to flip back depending on how permanent you want it:

- **For this conversation only**: type `/flint-off`. Flip forward with
  `/flint-on`. Doesn't touch settings.
- **For all future sessions**: `/config` → Output style → `default`, or
  remove `"outputStyle": "flint"` from `~/.claude/settings.json`.
- **For one-off questions without flipping at all**: use
  `/flint <question>` (one-shot) even if the session is in prose mode.

The skill is designed to be toggled. Don't try to force every turn through
it.

## Deployment-specific: Claude Code vs bare API

Flint's own behavior differs by deployment path. This is a first-class
failure mode worth understanding before you pick one.

### Bare Anthropic API (`system: flint_system_prompt.txt`)

This is the mode the stress bench measures. 98%+ IR trigger on IR-shape
tasks, 80% parseable by the shipped grammar, 186 output tokens mean on the
10-task corpus. The numbers on the README front page come from here.

### Claude Code via output-style only (`/config → flint` or `flint-thinking`)

Output-styles load as **context**, not system prompt. Claude Code's built-in
system prompt ("be helpful, return the useful answer") wins conflicts
silently. Measured on a 6-task mix, pure output-style delivers 0% IR
trigger on IR-shape tasks — you lose the compression entirely. The Caveman
discipline in `flint-thinking` still applies to prose output (tighter than
default Claude Code), but the IR half is gone. This is not a bug; it is
what the Claude Code architecture allows from context-layer instructions.

### Claude Code via `flint` wrapper (`--append-system-prompt`)

`flint` passes the thinking-mode prompt via `claude
--append-system-prompt`, the only Claude Code flag that reaches
system-prompt level. Measured classification accuracy: 100% on a 6-task
mix (3 IR-shape + 3 prose-shape), across 3 runs. Mean output tokens -22%
vs plain claude. IR trigger recovers to the level the API bench predicts.

**Recommendation by use case:**

- Building a product that calls Claude via API → strict Flint
  (`flint_system_prompt.txt`) as the system prompt. Parseable IR, full
  contract.
- Using Claude Code interactively on a Max plan → `flint` for
  always-on dual-mode (IR when warranted, Caveman prose otherwise). No
  interference with default `claude`.
- Occasional on-demand IR in normal Claude Code → `/flint <question>`
  slash command. One-shot.

### Parser-pass on Claude Code IR

Early versions of the thinking-mode prompt produced IR that was
human-readable but only ~17% parseable by the strict Flint grammar — the
model under `--append-system-prompt` was still using suffix forms like
`change_"x%2==0"` and nested calls like `cmp(expMs+skew_ms,"<",nowMs)` out
of coding-assistant habit.

The shipped v0.4.0 prompt includes an explicit ATOM FORMAT section with
concrete anti-examples of the drift patterns. Measured on the 6-prompt
claude-code-max corpus, 3 runs: 89% of IR-shape outputs (8 of 9) now parse
cleanly under the strict grammar. This is at or above strict Flint's own
baseline (~80% on the 10-task stress corpus).

Remaining ~11% failures cluster on two patterns the model still slips into:
- `identifier_"quoted"` (suffix form) — parser wants `identifier("quoted")`
- `→` inside call args — parser wants plain `∧` joins between atoms

If you need 100% parseability for downstream tooling, use strict Flint
via the Anthropic API directly with `flint_system_prompt.txt` as the
system prompt. For interactive Claude Code use `flint`; the 11%
non-parseable outputs remain fully human-readable and semantically correct.

## Multi-turn session drift

On multi-turn sessions inside Claude Code (where the client resumes a
session across several turns via `--resume`), `flint` reliably emits
Flint IR on **turn 1** and drifts to prose on subsequent turns.

Measured on 2 scenarios × 4 turns × 3 runs (24 samples), IR emission by
turn:

```
deep-debug-auth:  T1=IR 3/3  T2=prose 3/3  T3=prose 3/3  T4=IR 1/3
mixed-security:   T1=IR 3/3  T2=prose*3/3  T3=prose 3/3  T4=prose*3/3
                                 (*=prose-expected)
```

Turn 1 has the highest user-prompt salience for the system prompt's
Zone 3 rule ("IR when task has crisp goal and verifiable endpoint").
By turn 2, the prior assistant response (IR from T1) plus new user
message are interpreted by the model as "continuing an IR session" →
prose follow-up in chat register. The system prompt persists but loses
attention-weight against accumulated conversation context.

This is a Claude Code harness characteristic, not a Flint-specific
bug. The same pattern affects plain `claude` (which never emits IR at
all), `plain + MCP` (tool available, never called), and
`flint + MCP` (tool called at T1, not at T2-T4).

Workarounds:

- Open a fresh `flint` session per task: `flint -p "your task"`
  in non-interactive mode, or restart the interactive session for
  each distinct request.
- Use the `/flint` one-shot slash skill inside any session for a
  single IR answer on demand.
- For multi-turn sessions where flint is useful: the *prose*
  follow-ups are still Caveman-shape (no markdown headers, no filler),
  so total token usage drops -20% vs plain claude even with drift.
  Measured on 24 turns: flint 27404 tok vs plain 34248 tok.

## Bench methodology: agent-mode contamination

If you reproduce the multi-turn bench and see flint performing
**worse** than plain claude on `output_tokens`, you are hitting a
known pitfall: agent-mode contamination.

`claude -p` inherits permissions from user settings. By default on
most setups (including the shipped `defaultMode: auto`), Bash, Read,
Write, Edit, Grep, Glob, Task, and MCP tools can execute without a
prompt. If a scenario prompt contains agentic verbs ("write the test",
"propose the fix", "apply the change"), the model — especially under
flint's "CRISP + VERIFIABLE ENDPOINT" instruction — will go into
agent mode: it reads real files, writes real files, runs real shell
commands. Each tool call inflates `output_tokens` with tool_use args +
tool_result content.

A pre-v0.5.1 run of the 4-cell bench had flint at 14692 total tokens
vs plain 14316. Inspection showed that on deep-debug T2, flint
emitted 17 tool calls (11 × Bash, Read, Write, 3 × Edit, Grep) —
actually creating `auth/token_service.py` and `tests/test_token_refresh_race.py`
in the benchmark working dir. Plain claude on the same turn used only
2 tools. The reported tokens measured "how hard did the variant work",
not "how compact is the response".

Fix:

- **Scenario prompts** should use descriptive verbs only ("describe",
  "show inline", "as a snippet in your response") and explicitly
  instruct "do not create or modify files".
- **Bench script** injects `[BENCH MODE] Do not use any tools` at the
  end of every user prompt. The bench script in this repo does this
  automatically for all cells except `flint + MCP` (which allows
  `submit_flint_ir` only).
- **Scorer** (`claude_code_max_4cell_table.py`) tracks `agent_n` —
  turns where a non-Flint tool was called — and reports `clean_tok` in
  addition to raw `total_tok`. On the v0.5.1 bench all cells showed
  `agent_n = 0/24`.

The CLI `--disallowedTools` flag is easily bypassable (the model
falls back to MCP tools like `mcp__plugin_serena_serena__execute_shell_command`
which are not in the filter). The in-prompt directive is empirically
reliable across cells and models.

## Reporting a new failure mode

If you find a case where Flint produces a wrong or misleading answer — not
just a syntactic drift, but actually gets the technical content wrong —
please open an issue with:

- the exact prompt
- the model and date
- the response (raw)
- what you expected vs what you got

Tag it `failure-mode`. These are the reports that move the methodology
forward; style drift is easy to fix, semantic failure is the thing worth
tracking.
