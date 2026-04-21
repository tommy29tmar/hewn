# Hewn

**Claude Code wrapper that routes every turn to a compact answer shape.**

Hewn is a small `bash` wrapper around `claude` that does two things:

1. Appends a thinking-mode **system prompt** that routes each user turn to one
   of six answer shapes (IR, prose+code, prose-findings, prose-polished,
   prose-polished+code, prose-caveman) based on task structure.
2. Registers a per-turn **drift-fix hook** that classifies every prompt and
   re-injects the routing directive as `additionalContext`, preventing the
   T2+ drift observed when the system prompt alone does the routing.

The result: shorter, more structured answers on technical work, unchanged
prose on writing tasks, and consistent behavior across a multi-turn session.

The default `claude` binary is untouched. Hewn is an opt-in separate command.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/tommy29tmar/hewn/main/integrations/claude-code/install.sh | bash
```

Requires: Claude Code already installed (`~/.claude` must exist) and
`~/.local/bin` on `$PATH`.

## Usage

```bash
hewn                     # interactive session
hewn -p "your prompt"    # non-interactive
```

Any flag accepted by `claude` is forwarded.

## What gets installed

- `~/.local/bin/hewn` — the wrapper
- `~/.claude/hewn_thinking_system_prompt.txt` — the routing prompt
- `~/.claude/hooks/hewn_drift_fixer.py` — the UserPromptSubmit classifier
  (pure Python stdlib, runs in <10ms)

At runtime the wrapper generates a short temp `--settings` JSON that points
Claude Code's hook dispatcher at the classifier.

## The six routes

| Shape | When | Output |
|---|---|---|
| **IR** | crisp technical goal + verifiable endpoint, no code artifact asked | six-line `@hewn v0 hybrid` / G / C / P / V / A |
| **prose+code** | technical goal + asks for code, test, patch, snippet | terse analysis + fenced code |
| **prose-findings** | ranked/listed independent findings (bugs, risks, vulns) | numbered list with evidence per item |
| **prose-polished** | leadership / customer / stakeholder audience, no code | professional readable prose |
| **prose-polished+code** | polished audience + inline code, config, snippet, or patch | professional prose + fenced code |
| **prose-caveman** | chat, brainstorm, tutorial, quick explanation | terse compressed prose |

The classifier is a score-based regex match over the user prompt. See
`integrations/claude-code/hooks/hewn_drift_fixer.py` for the rules.

## Upgrading from Flint

Hewn is the hard-cutover continuation of the earlier Flint project. If you
previously installed Flint, clean up legacy files before re-installing:

```bash
rm -rf \
  ~/.claude/skills/flint ~/.claude/skills/flint-on \
  ~/.claude/skills/flint-off ~/.claude/skills/flint-audit \
  ~/.claude/output-styles/flint.md ~/.claude/output-styles/flint-thinking.md \
  ~/.claude/output-styles/hewn.md ~/.claude/output-styles/hewn-thinking.md \
  ~/.claude/flint_thinking_system_prompt.txt \
  ~/.claude/flint_thinking_mcp_system_prompt.txt \
  ~/.claude/flint_system_prompt.txt \
  ~/.claude/flint-drift-fix-settings.json \
  ~/.claude/flint-mcp-config.json \
  ~/.claude/hooks/flint_drift_fixer.py
rm -f ~/.local/bin/flint ~/.local/bin/flint-mcp \
      ~/.local/bin/hewn-mcp ~/.local/bin/cccaveman
```

The MCP server, Python parser/audit CLI, skills, and output styles from the
Flint era are no longer part of the project. Git history preserves them.

## Uninstall

```bash
rm -f ~/.local/bin/hewn \
      ~/.claude/hewn_thinking_system_prompt.txt \
      ~/.claude/hooks/hewn_drift_fixer.py
```

## License

MIT. See [LICENSE](LICENSE) and [CITATION.cff](CITATION.cff).
