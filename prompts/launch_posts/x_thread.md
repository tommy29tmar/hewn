# X / Twitter thread draft

Pin the hero image (hero.jpg) on tweet 1. Attach the demo.png comparison
on tweet 4. Post between 9-11 AM ET or 7-9 PM ET.

---

**Tweet 1 (hook + image)** — attach `assets/launch/hero.jpg`

> You've heard of caveman prompting.
>
> Tell Claude to drop articles, save ~40% tokens.
>
> It works. It also drops concepts.
>
> Meet Flint. Compresses the work, not the words.
>
> github.com/tommy29tmar/flint

*(~220 chars; caveman+flint image does the emotional lift)*

---

**Tweet 2 (the numbers)**

> Claude Opus 4.7. 10 long-context coding tasks. 40 samples per cell.
>
> verbose:  736 tok · 15s · 86% concepts
> caveman:  423 tok ·  9s · 84% concepts
> FLINT:    186 tok ·  5s · 95% concepts
>
> 4× shorter. 3× faster. +9pt accuracy.
> Wins every column.

*(~260 chars)*

---

**Tweet 3 (why it works)**

> Caveman compresses the voice: "drop the, a, an."
>
> Flint compresses the structure: five slots, one operator `∧`, atoms only.
>
> G: goal
> C: constraints
> P: plan
> V: verify
> A: action
>
> The shape is the compression. And the checklist.

*(~250 chars)*

---

**Tweet 4 (proof image)** — attach `assets/launch/demo.png`

> Same question. Same model. Same context.
>
> Claude default: 736 tokens, 15s.
> Claude + Flint: 186 tokens, 5s.
>
> Same bug, same fix, same verification plan, same risk flags.
>
> The [AUDIT] block still reads as plain English for humans.

---

**Tweet 5 (install)**

> One install. MIT.
>
> curl -fsSL https://raw.githubusercontent.com/tommy29tmar/flint/main/integrations/claude-code/install.sh | bash
>
> In Claude Code:
>    /flint <question>                      one-shot
>    /config → Output style → flint         every response (strict)
>    cccflint                               always-on for Claude Code Max
>
> Off: same menu, pick default. `cccflint` never shadows the default `claude`.

---

**Tweet 6 (honest scope + repo)**

> Flint shines on technical asks: debug, review, refactor, architecture.
>
> It's NOT for essays, chat, or creative writing. Use Claude normally for those.
>
> Methodology, failure modes, and full bench:
> github.com/tommy29tmar/flint
>
> ← open issues with "failure-mode" tag if it breaks for you.

---

## Alternate opener (if the first one doesn't land in 30 min)

**Alt tweet 1**

> Anthropic's Claude Opus 4.7 is great. It's also expensive.
>
> I shipped Flint: a 90-token system prompt that cuts output tokens **4×** on long-context coding tasks — and increases concept coverage by 9 points.
>
> Not a caveman-voice trick. A compiler-style IR.
>
> github.com/tommy29tmar/flint

*(use if the hook-first version feels too cute for the moment; this one leans into the 4.7 news window)*

---

## Post-launch follow-ups (queue for day 2-7)

1. **Day 2** — "Here's the prompt. 8 lines. That's the whole thing." Quote-tweet
   a pic of `flint_system_prompt.txt`. Invite screenshots of what people ran
   through it.
2. **Day 3** — "Someone asked why Flint wins on concept coverage when it's
   shorter. The answer is that Claude's verbose mode spends ~30% of its tokens
   on transitions. Flint makes atoms per token much higher. Thread ↓"
3. **Day 5** — day-1 data thread: installs, top issues, favorite failure mode.
4. **Day 7** — if someone uses Flint in a real product, retweet with 1-line
   commentary.

## v0.4.0 follow-up (Claude Code Max always-on)

**Post 1 — the discovery**

> Turns out Claude Code's output-style loads as *context*, not system
> prompt. Your "always-on Flint" via /config → Output style works — for
> prose compression. The IR half silently loses to Claude Code's built-in
> "be helpful" system prompt.
>
> Fix: `cccflint`. System-level injection via `--append-system-prompt`.
> The only path that actually works.

**Post 2 — the numbers**

> 6 mixed prompts (debug/review/refactor · explain/brainstorm/RFC), 3 runs.
> Claude Max, zero API cost.
>
> plain `claude`:  50% task-shape accuracy, 537 out tok mean
> `cccflint`:     100% task-shape accuracy, 421 out tok mean (-22%)
>
> Always-on for Claude Code users is now real. `cccflint` ships in v0.4.0.

**Post 3 — non-invasive opt-in**

> `cccflint` is a separate binary, ~40 lines of bash. The default `claude`
> command is never touched. You opt in by typing `cccflint` instead.
>
> Anthropic's product works as designed; Flint layers on top without
> shadowing it. That's how extensions should behave.
