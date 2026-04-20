# Architecture

What Flint actually is, as a system, from the IR on the wire down to the CLI
on your machine.

## The artifacts that ship

Flint deploys two complementary payloads — strict (for API use) and
thinking-mode (for Claude Code Max users):

| artifact | path | size | contract |
|---|---|---|---|
| Strict Flint system prompt | `integrations/claude-code/flint_system_prompt.txt` | 8 lines, ~90 tokens | force every response into G/C/P/V/A IR |
| Thinking-mode system prompt | `integrations/claude-code/flint_thinking_system_prompt.txt` | 32 lines, ~270 tokens | dual-mode: Caveman prose by default, IR when task shape is IR (debug/review/refactor with verifiable endpoint) |
| `cccflint` wrapper | `integrations/claude-code/bin/cccflint` | small bash wrapper | runs `claude --append-system-prompt <thinking_prompt>` so the instruction reaches system-prompt level inside Claude Code |

The strict prompt is the API-facing artifact (output-style `flint`). The
thinking-mode prompt is the Claude Code always-on artifact (`cccflint` or
output-style `flint-thinking`).

Everything else in this repo — the parser, the verifier, the
`flint audit --explain` CLI, the tests, the benches — exists to validate,
measure, and repair what comes back.

### Why two payloads, not one

On the Anthropic API directly, the strict prompt IS the system prompt —
contract respected, 98%+ IR trigger on IR-shape tasks, 80% parseable.
Benchmark-ready, deterministic.

In Claude Code, `/config → Output style → flint` loads the prompt as
**context**, not system. Claude Code's built-in system prompt ("be helpful,
return the useful answer") wins any conflict. Output-style instructions
asking for strict IR lose silently — in our measurements, 0% IR trigger on
IR-shape tasks when the strict prompt is loaded via output-style alone.

The thinking-mode prompt + `cccflint` wrapper solve this. `cccflint` passes
the prompt via `claude --append-system-prompt`, the only Claude Code
mechanism that reaches system level. Measured classification accuracy
jumps from 50% (plain claude) to 100% (cccflint) on a 6-task × 3-run mix
of IR and prose tasks; mean output tokens drop 22% across the mix.

Hooks, skills, and CLAUDE.md also load as context. They cannot replicate
system-level behavior. The wrapper is the only path.

## The four slash commands

The installer also drops four Claude Code skills under `~/.claude/skills/`:

| command | scope | file |
| --- | --- | --- |
| `/flint <question>` | one turn | `skills/flint/SKILL.md` |
| `/flint-on` | rest of this conversation | `skills/flint-on/SKILL.md` |
| `/flint-off` | return to prose for this conversation | `skills/flint-off/SKILL.md` |
| `/flint-audit <file\|paste>` | decode a Flint doc to prose | `skills/flint-audit/SKILL.md` |

The first three are prompt-level — they instruct the model to emit (or
stop emitting) Flint for the specified scope. The fourth invokes the
`flint audit --explain` CLI under the hood, so it works on any saved
Flint document.

Cross-session persistence (every new Claude Code session starts in Flint)
is handled separately by the Output Style system — see the section above.
The `/flint-on`/`off` pair is a per-conversation convenience; it doesn't
touch `settings.json`.

## The IR

Flint is a compact symbolic IR (intermediate representation) with five
slots, one operator, and one header line.

```
@flint v0 hybrid
G: <goal atom>
C: <context atoms joined with ∧>
P: <plan atoms joined with ∧>
V: <verification atoms joined with ∧>
A: <action atoms joined with ∧>
```

Five slots, one operator, two escape hatches:

| slot | meaning | typical content |
| --- | --- | --- |
| **G** | goal | the thing to accomplish, as 1 atom |
| **C** | context and constraints | what's true in the world the answer has to respect |
| **P** | plan | the ordered steps |
| **V** | verification | how you'd check the answer worked |
| **A** | action | the concrete move — patch, command, config change |

The operator `∧` (logical AND) joins atoms. Two prefix markers are reserved:
`!` marks a high-risk atom, `?` marks an uncertain one. An optional `[AUDIT]`
trailer (activated by the `hybrid` mode) renders the same content as plain
prose for humans.

The full grammar is at [`FLINT_GRAMMAR.ebnf`](../FLINT_GRAMMAR.ebnf).
ASCII-safe operator aliases for models that mangle Unicode are at
[`grammar/flint_ascii.md`](../grammar/flint_ascii.md).

## Atoms

An atom is the smallest unit of meaning Flint allows. It must be one of:

- a snake_case identifier: `fix_auth_expiry`, `trust_boundary`
- a call-form function: `expire("10m")`, `bind(req.ip)`
- a quoted literal: `"X-Forwarded-For"`, `"500"`
- a single symbol reference from the optional `@cb[...]` codebook block

Echoing literal anchors from the user's question verbatim (numbers,
identifiers, code tokens, schema names) is part of the contract: the parser
preserves them byte-for-byte, and the verifier checks for them.

## The pipeline

```
user question + flint_system_prompt  →  Claude  →  raw response
                                                       │
                                                       ▼
                                              src/flint/normalize.py
                                              (whitespace, case, unicode,
                                               drift-tolerant repair)
                                                       │
                                                       ▼
                                               src/flint/parser.py
                                              (strict grammar, stdlib only)
                                                       │
                                                       ▼
                                            src/flint/verification.py
                                            (anchors matched, slots complete,
                                             operators valid, no drift)
                                                       │
                                                       ▼
                                               src/flint/render.py
                                           (prose rerender for humans,
                                            optional [AUDIT] block)
```

### normalize.py

Before the parser sees anything, the normalizer runs. It's a list of
permissive transforms that handle common model drift:

- unicode operators swapped for ASCII fallbacks when the model emits one of
  the aliases (`&` → `∧`, `=>` → `⇒`, `->` → `→`)
- stray `SIGIL:` or `Flint:` lead-in labels stripped (left over from
  older training)
- call form canonicalized: `ddl_"12 weeks"` → `ddl("12 weeks")`
- whitespace collapsed, trailing commas dropped, blank lines removed

The normalizer is **deterministic** and local — no LLM roundtrip. If you
want to see exactly what it did to a response, run:

```bash
flint repair response.flint        # prints normalized version to stdout
flint audit --explain response.flint   # shows before/after + verdict
```

### parser.py

Strict recursive-descent parser, Python stdlib only. The grammar is small
enough to fit in one file (`FLINT_GRAMMAR.ebnf` is the full spec). On parse
failure the parser returns the exact offset and what it expected, which the
verifier converts into a human error.

### verification.py

Three checks:

1. **Schema**: all five required slots present, header well-formed, no
   extraneous output.
2. **Anchors**: every literal anchor passed as `--anchor` matches somewhere
   in the document (used by the bench's `must_include` check).
3. **Drift**: the `[AUDIT]` block, if present, doesn't contradict the
   symbolic slots. This is a cheap heuristic, not a semantic proof.

Anything that fails falls into one of three buckets: `repairable` (the
normalizer can fix it), `schema_error` (the IR is malformed), or
`content_error` (the anchor didn't land).

### render.py

Takes a parsed Flint document and emits plain prose. This is what
`[AUDIT]` contains — the model can pre-render it itself in `hybrid` mode, or
you can generate it locally from the parsed tree. Useful when a human needs
to read the answer without learning the IR.

## CLI

```bash
flint validate <file.flint>             # parse + verify, exit non-zero on fail
flint parse <file.flint>                # dump parse tree
flint audit <file.flint>                # render the prose view
flint audit --explain <file.flint>      # verbose: show normalize, parse, anchors
flint stats <file.flint>                # tokens, slots, atoms counts
flint repair <file.flint>               # normalize-only, print to stdout
flint claude-code inventory <md>        # token accounting for CLAUDE.md files
flint claude-code diff <md>             # safe-compress preview, read-only
flint routing [profile]                 # inspect variant routing profiles
```

All commands are stdlib only, no network calls, no LLM roundtrips. The
network is only touched by the bench harness (`evals/run_anthropic.py`).

## Modes

The header `@flint v0 <mode>` selects one of five behaviors:

- `draft` — return IR only, no audit
- `audit` — return a short prose summary, no IR
- `hybrid` — IR + `[AUDIT]` block (the default used by the shipped skill)
- `memory` — return compact memory capsules (used in agent-loop experiments)
- `compile` — return codebook + IR + expansion targets + verification list

The shipped skill uses `hybrid` because it's the mode that survives best
when the user needs to read the answer without learning the IR.

## What isn't in the IR (on purpose)

- **No unlimited nesting.** Slots are flat. Nested structures would require
  recursive parsing and would invite the model to hide complexity inside
  sub-slots.
- **No free-form prose inside slots.** A slot is `atom (∧ atom)*`, full
  stop. If you need prose, it goes in the `[AUDIT]` trailer.
- **No imports, no includes, no references across messages.** Flint is
  per-message. A conversation is a sequence of independent Flint documents.
- **No code blocks.** If the answer is a code patch, the A slot points at
  the patch; the patch itself goes in a normal fenced block *outside* the
  Flint document. Flint describes, doesn't embed.

## Why this shape

The IR is a compiler trick applied to prompting: freeze the grammar, freeze
the artifact, measure the artifact. Every byte of the shipped prompt is
load-bearing; every Flint document the model produces is mechanically
parseable, mechanically verifiable, and mechanically renderable back to
prose.

That's the contract. Everything else in this repo exists to check that the
contract holds on your data.
