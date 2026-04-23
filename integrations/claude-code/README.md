# Hewn — Claude Code integration

Hewn is a Claude Code CLI wrapper for long sessions under tight limits.
It runs `claude` with:

- A thinking-mode **system prompt** appended via `--append-system-prompt`,
  which routes each turn to one of six shapes (IR, prose+code,
  prose-findings, prose-polished, prose-polished+code, prose-caveman)
  based on task structure.
- A per-turn **drift-fix hook** registered via `--settings`, which
  classifies every user prompt and re-injects the routing directive as
  `additionalContext`. This prevents the long-session drift observed when relying
  on the system prompt alone.

Together these two pieces keep Claude Code compact turn after turn
instead of letting long sessions drift back into output-heavy prose.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/tommy29tmar/hewn/main/integrations/claude-code/install.sh | bash
```

## Usage

```bash
hewn                     # interactive session with Hewn long-session routing
hewn -p "your prompt"    # non-interactive
```

Any flag accepted by `claude` is forwarded: `hewn --model claude-opus-4-7 -p "…"`.

The default `claude` command is untouched. Use `hewn` when you want
Claude Code to stay tighter over a long session; use `claude` when you
want stock behavior.

## Locales

Shipped locales: `en`, `it`, `es`, `fr`, `de`. All five are validated at
100% coverage on a 12-prompt realistic corpus spanning every route.
`en` and `it` additionally draw from real-prompt history; `es`/`fr`/`de`
patterns were synthesized from the Italian baseline — PRs expanding them
with more real-prompt evidence are welcome at `hooks/locales/<code>.py`.

### Resolution precedence

From highest to lowest:

1. **`--locale` flag** on the wrapper (per-invocation).
2. **`HEWN_LOCALE` env var** (persistent across sessions).
3. **`$LC_ALL` / `$LC_MESSAGES` / `$LANG` auto-detect** — if the 2-letter
   prefix matches a shipped locale, it's stacked on top of English.
   Example: `LANG=it_IT.UTF-8` loads `en + it` automatically.
4. **English-only** fallback. Applies when the system locale is
   `C`/`POSIX`/`en_*` or a language Hewn doesn't ship patterns for.

### Examples

```bash
hewn                       # auto-detect from $LANG (most users need nothing)
hewn --locale en,it        # force en+it for this invocation
hewn --locale=fr -p "…"    # headless with French stacked
export HEWN_LOCALE=en,es   # persistent Spanish in your shell rc
export HEWN_LOCALE=en      # force English-only despite a non-English shell
```

The `--locale` flag wins over `HEWN_LOCALE`, which wins over auto-detect.

## Files installed

- `~/.local/bin/hewn` — the wrapper
- `~/.claude/hewn_thinking_system_prompt.txt` — the system prompt
- `~/.claude/hooks/hewn_drift_fixer.py` — the UserPromptSubmit hook
- `~/.claude/hooks/locales/{en,it,es,fr,de}.py` — locale patterns

## Uninstall

```bash
rm -f ~/.local/bin/hewn \
      ~/.claude/hewn_thinking_system_prompt.txt \
      ~/.claude/hooks/hewn_drift_fixer.py
rm -rf ~/.claude/hooks/locales
```
