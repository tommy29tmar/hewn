# Evidence — T2 / `login-button-broken`

## Prompt

```text
the login button doesnt work people are complaining help
```

## `baseline`

output_tokens (anthropic) = **227**, output_tokens (tiktoken) = 48, input_tokens = 6, cache_creation = 15818, cache_read = 16796, latency wall = 4985ms (median across runs: 4985ms)

```text
There's no login button in this repo — it's Hewn, a Claude Code CLI wrapper (no UI, no auth). Are you in the wrong directory, or talking about a different project? If so, point me at the repo path.
```

## `terse`

output_tokens (anthropic) = **93**, output_tokens (tiktoken) = 59, input_tokens = 6, cache_creation = 10491, cache_read = 13741, latency wall = 3396ms (median across runs: 3396ms)

```text
Need more info to help:

1. Which repo/app? (path or URL)
2. What happens when clicking — nothing, error, redirect loop, 500?
3. Browser console / network errors?
4. Recent changes to auth code?

Point me at the code and I'll investigate.
```

## `caveman_full`

output_tokens (anthropic) = **122**, output_tokens (tiktoken) = 79, input_tokens = 6, cache_creation = 0, cache_read = 25677, latency wall = 4849ms (median across runs: 4849ms)

```text
Need info. What stack? What happen on click — nothing, error, redirect fail? Console errors? Recent deploy?

Quick check list:
1. Open devtools → Console + Network tab
2. Click button → see error?
3. Button have `onClick` / form `action` wired?
4. Auth endpoint return 200?

Paste error or repo path, me fix.
```

## `caveman_full_plus_ultra_directive`

output_tokens (anthropic) = **106**, output_tokens (tiktoken) = 67, input_tokens = 6, cache_creation = 10490, cache_read = 15201, latency wall = 4063ms (median across runs: 4063ms)

```text
Need info. Which app? Repo path? Error msg/console log? Reproducible URL?

Fastest path: run `/gstack-investigate` — root cause loop. Or paste:
- Repo/dir
- Login page URL
- Console + network tab errors
- Recent commits touching auth

Then me debug.
```

## `hewn_prompt_only`

output_tokens (anthropic) = **182**, output_tokens (tiktoken) = 52, input_tokens = 6, cache_creation = 15818, cache_read = 16796, latency wall = 4740ms (median across runs: 4193ms)

```text
There's no login button here — this repo is Hewn, a Claude Code CLI wrapper. No web app, no auth, no users logging in.

Are you thinking of a different project? If so, `cd` into it and I'll take a look.
```

## `hewn_full`

output_tokens (anthropic) = **236**, output_tokens (tiktoken) = 79, input_tokens = 6, cache_creation = 0, cache_read = 34097, latency wall = 5775ms (median across runs: 5808ms)

```text
no login button in this repo
SIGIL = Hewn, CLI wrapper for Claude Code
no web UI, no auth, no users to complain
sure you're in right project?
if you meant different repo, point me at it
or describe what "login" you mean here — maybe `hewn` auth to Claude API? that's just `ANTHROPIC_API_KEY` env
```
