# Claude Code Integration

Flint can be used from Claude Code in two practical ways:

1. `CLAUDE.md` for interactive terminal sessions
2. `--append-system-prompt` for `claude -p` print-mode wrappers

Anthropic's official docs say Claude Code can be customized with project `CLAUDE.md` files or `--append-system-prompt`, and that model choice can be changed with `/model`, `--model`, or environment variables.

Relevant docs:

- Settings: https://docs.anthropic.com/en/docs/claude-code/settings
- CLI reference: https://docs.anthropic.com/en/docs/claude-code/cli-reference
- Model configuration: https://support.anthropic.com/en/articles/11940350-claude-code-model-configuration

## Install

See the top-level [README](../../README.md) for the one-liner install and the `/flint` + `/output-style flint` workflow.

## Usage model

The generated `CLAUDE.md` keeps normal human-language answers as the default and reserves raw Flint for:

- explicit Flint requests
- compact capsule generation
- benchmark or tool-driven symbolic transport

That matches Claude Code better than forcing every terminal reply into raw symbolic form.

## Per-file `CLAUDE.md` audit

Flint ships a read-only CLI for auditing individual markdown instruction files. It is **per-file**: you point it at a specific `CLAUDE.md` (or any markdown). It does **not** walk your filesystem, does **not** enumerate or mirror Claude Code's memory-resolution rules, and never modifies the original file.

```bash
# Token accounting for one or more files
flint claude-code inventory path/to/CLAUDE.md

# Print a structurally-safe compressed copy to stdout (preserves fenced code,
# command lines, paths, inline-code paragraphs, headings; collapses only
# runs of whitespace inside plain prose bullets)
flint claude-code compile path/to/CLAUDE.md

# Unified diff of original vs compressed, plus per-segment summary
flint claude-code diff path/to/CLAUDE.md
```

What the compiler refuses to touch:

- fenced code blocks (` ``` ` / `~~~`)
- markdown headings
- lines that look like shell commands (`$`, `>`, `#!`) or filesystem paths
- list items containing backticks (inline code)
- any paragraph that is not an explicit list item

What it *does* touch: plain list-item prose, and only to collapse runs of whitespace. Words, punctuation, and operators are never rewritten. If collapsing would change any non-whitespace character, the original text is returned unchanged.

Cache lives under `~/.cache/flint/claude-code/` keyed on sha1 of the original file; override with `FLINT_CACHE_DIR` or pass `--no-cache`.
