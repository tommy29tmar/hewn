# Hewn — Claude Code integration

Hewn is a Claude Code CLI wrapper. It runs `claude` with:

- A thinking-mode **system prompt** appended via `--append-system-prompt`,
  which routes each turn to one of five shapes (IR, prose+code,
  prose-findings, prose-polished, prose-caveman) based on task structure.
- A per-turn **drift-fix hook** registered via `--settings`, which
  classifies every user prompt and re-injects the routing directive as
  `additionalContext`. This prevents the T2+ drift observed when relying
  on the system prompt alone.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/tommy29tmar/hewn/main/integrations/claude-code/install.sh | bash
```

(During the GitHub repo rename from `flint` → `hewn`, the old URL still
works via redirect.)

## Usage

```bash
hewn                     # interactive session with Hewn thinking-mode
hewn -p "your prompt"    # non-interactive
```

Any flag accepted by `claude` is forwarded: `hewn --model claude-opus-4-7 -p "…"`.

The default `claude` command is untouched.

## Files installed

- `~/.local/bin/hewn` — the wrapper
- `~/.claude/hewn_thinking_system_prompt.txt` — the system prompt
- `~/.claude/hooks/hewn_drift_fixer.py` — the UserPromptSubmit hook

## Uninstall

```bash
rm -f ~/.local/bin/hewn \
      ~/.claude/hewn_thinking_system_prompt.txt \
      ~/.claude/hooks/hewn_drift_fixer.py
```
