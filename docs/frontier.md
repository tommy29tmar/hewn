# Frontier Directions

Flint is strongest when treated as a layered system rather than a single prompt trick.

## 1. Text-First Flint

This is the simplest lane:

- prompt the model directly into Flint text
- parse the result
- measure raw parse rate

Strengths:

- works on almost any modern model
- cheapest way to iterate on syntax and semantics

Weaknesses:

- raw parseability is fragile
- prompt drift can reintroduce prose

## 2. Schema-First Flint

This is the strongest current engineering direction.

Pipeline:

1. model emits structured JSON under a strict schema
2. local renderer turns that JSON into Flint text
3. parser validates the rendered document

Why this matters:

- macro-structure is enforced by Structured Outputs
- micro-syntax can also be constrained with regex patterns
- the renderer becomes deterministic and auditable

This architecture is closer to how serious compilers and toolchains are built.

## 3. Repairable Flint

The runtime should distinguish:

- raw parse rate
- repair parse rate

That split matters because:

- prompt quality measures how often the model emits clean IR directly
- repair quality measures how resilient the transport is in production

Near-miss syntax failures should not be treated the same as semantic failures.

## 4. Task-Specific Micro-IRs

A single universal schema is probably not the end state.

The stronger direction is a family of small IRs:

- debugging IR
- code-review IR
- architecture-decision IR
- refactor IR
- memory-capsule IR

All of them can compile down to the same surface Flint syntax, but their transport schemas should be specialized.

This is likely the path to improving both quality and compression at once.

## 5. Cache-Aware Flint

If Flint becomes a real product, speed gains will come from more than shorter outputs.

Use:

- prompt caching for static Flint system prefixes and schemas
- compact memory capsules instead of verbose repo summaries
- deterministic renderers so cache hits apply across runs

This matters because a compact IR plus cache reuse can reduce both token cost and latency.

## 6. Literal-Aware Transport

The transport layer must preserve exact literals without collapsing back into prose.

The current practical rule is:

- keep compact atoms by default
- allow quoted literal arguments when exact strings matter
- never normalize away critical code or prompt literals if they affect verification

This matters because some early semantic loss came from the schema grammar itself being too restrictive.

## 7. Wire Protocol Flint

There is now a strong distinction between:

- transport schema
- rendered Flint document
- human audit materialization

The strongest current pattern is:

- emit a compact typed wire object
- render Flint locally
- synthesize the audit locally when possible

This is closer to wire-protocol design than prompt design.

Why this matters:

- the provider should pay for transport, not for repeated explanatory phrasing
- compact keys and omitted audit text reduce output burden
- the runtime can still reconstruct a parseable symbolic artifact

This is conceptually closer to Protocol Buffers and other compact transport layers than to “inventing a funny language”.

## 8. Lite Transport Plus Local Canonicalization

The strongest new result is not just a smaller wire schema.

It is:

- lighter provider-side constraints
- local canonicalization of relaxed fields
- deterministic render into the canonical Flint surface form

This is a compiler move:

- accept a cheaper front-end contract
- normalize locally
- preserve a stable downstream IR

That pattern is likely more scalable than forcing maximal structure at generation time.

## 9. Compiler-First Direct Flint

The strongest new path in the repo is not a smaller schema.

It is:

1. compile the long task into a deterministic micro capsule
2. ask the model for direct Flint, not JSON
3. repair small syntax drift locally
4. synthesize audit locally

Why this matters:

- it removes most schema-side input overhead
- it keeps a parseable symbolic artifact
- it is the first lane that beats the original natural-language baseline on total tokens with a strong model

The caveat is equally important:

- the same approach still loses to a terse baseline that also receives the compiled capsule on `gpt-5.4-mini`

So the real frontier is not “more symbolic text”.

It is:

- local compilation
- direct low-overhead transport
- deterministic repair
- model-aware routing

The new practical nuance is that this lane has a narrow optimum on smaller strong models:

- a fully typed prompt is too expensive
- an overcompressed prompt stops anchoring the format
- the best current prompt family is a mid-point `compact` contract, not the shortest one

## 10. Routed Transport Policy

The best result so far is not one universal schema.

It is a router:

- debugging → compact wire lane
- code review → compact wire lane
- architecture → direct descriptive schema lane
- refactor → direct descriptive schema lane

This resembles multi-level compiler systems more than template prompting:

- different task families use different micro-IRs
- shared downstream tooling operates through a common interface
- the transport decision becomes a policy problem

The MLIR idea of decoupling transformations from dialect-specific details is a useful analogy here.

## 11. Learned Routing Profiles

Routing should not stay hand-written forever.

The repo now has enough machinery to suggest profiles automatically from benchmark runs.

This matters because:

- different objectives imply different routers
- quality-first and efficiency-first are genuinely different policies
- routing can become a measured artifact that evolves with new eval data

## 12. Draft-Conditioned Transport

Two-stage transport is now a real benchmark lane:

1. free draft
2. constrained final render

This is inspired by draft-conditioned constrained decoding work, but the current Flint result is negative:

- validity stays high
- total token cost rises sharply
- latency rises sharply
- measured quality did not improve on the current task set

So this lane should be treated as:

- optional fallback
- maybe useful for harder tasks
- not the default production path

## 13. Mini-Model Wall

The most honest wall is now specific.

It is not parseability.

It is this:

- smaller strong models already compress terse natural language very well
- if the baseline also gets a compiled local capsule
- direct Flint still pays too much prompt-contract overhead

That suggests the next frontier is:

- even shorter direct prompts
- prefix reuse or cache hits that actually materialize
- model-family-specific micro-IRs
- provider-native grammar constraints beyond JSON schema

The last round of experiments adds one more conclusion:

- prompt-only tuning is still moving the wall
- but the remaining gap is now small enough that another pure prompt iteration may not be the highest-leverage next step

## 14. Future Research Track

Prompt-only Flint is only phase one.

The deeper research direction is:

- codebook induction from repo/task statistics
- tokenizer-aware symbol selection
- structured transport tuned per model family
- distillation of Flint outputs into smaller fast models
- latent/discrete backends for the highest-frequency reasoning motifs

The likely winning stack is not:

> one magical compact language

It is:

> typed micro-IRs + constrained generation + deterministic rendering + adaptive expansion
