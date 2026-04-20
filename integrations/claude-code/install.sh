#!/usr/bin/env bash
# Flint — Claude Code skill installer.
# One-line install:
#   curl -fsSL https://raw.githubusercontent.com/tommy29tmar/flint/main/integrations/claude-code/install.sh | bash
#
# What this does:
#   1. Installs four Claude Code skills: /flint, /flint-on, /flint-off, /flint-audit.
#   2. Installs the Flint output-styles: `flint` (strict) and `flint-thinking` (dual-mode).
#   3. Installs `cccflint`: wrapper that invokes `claude` with Flint thinking-mode at
#      system-prompt level via --append-system-prompt. This is the always-on path for
#      Claude Code Max users — does NOT interfere with the default `claude` binary.
#   4. Installs the flint-ir Python package (provides the `flint` CLI for parse/rerender).
#
# Refuses to run if ~/.claude is not present (i.e. Claude Code not installed).

set -euo pipefail

CLAUDE_DIR="${HOME}/.claude"
REPO_URL="https://github.com/tommy29tmar/flint.git"
RAW_URL="https://raw.githubusercontent.com/tommy29tmar/flint/main"

SKILLS=(flint flint-on flint-off flint-audit)

if [ ! -d "$CLAUDE_DIR" ]; then
  echo "error: ~/.claude not found. Install Claude Code first."
  exit 1
fi

# Detect if running from a repo checkout (for local testing). Otherwise curl down.
# When piped via `curl | bash`, BASH_SOURCE is empty and SCRIPT_DIR stays empty.
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"
fi
IS_LOCAL=0
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/skills/flint/SKILL.md" ]; then
  IS_LOCAL=1
fi

fetch() {
  local rel="$1"
  local dest="$2"
  if [ "$IS_LOCAL" = "1" ]; then
    cp "$SCRIPT_DIR/$rel" "$dest"
  else
    curl -fsSL "$RAW_URL/integrations/claude-code/$rel" -o "$dest"
  fi
}

for skill in "${SKILLS[@]}"; do
  echo "==> Installing /$skill skill"
  mkdir -p "$CLAUDE_DIR/skills/$skill"
  fetch "skills/$skill/SKILL.md" "$CLAUDE_DIR/skills/$skill/SKILL.md"
done

echo "==> Installing Flint output-styles"
mkdir -p "$CLAUDE_DIR/output-styles"
fetch "output-styles/flint.md" "$CLAUDE_DIR/output-styles/flint.md" || \
  echo "   (flint output-style install failed — skills alone are sufficient)"
fetch "output-styles/flint-thinking.md" "$CLAUDE_DIR/output-styles/flint-thinking.md" || \
  echo "   (flint-thinking output-style install failed — not fatal)"

echo "==> Installing cccflint wrapper + thinking-mode prompt"
BIN_DIR="${HOME}/.local/bin"
mkdir -p "$BIN_DIR"
fetch "bin/cccflint" "$BIN_DIR/cccflint" || echo "   (cccflint install failed — not fatal)"
chmod +x "$BIN_DIR/cccflint" 2>/dev/null || true
fetch "flint_thinking_system_prompt.txt" "$CLAUDE_DIR/flint_thinking_system_prompt.txt" || \
  echo "   (thinking-mode prompt install failed — cccflint will not work until installed)"

if ! echo ":$PATH:" | grep -q ":$BIN_DIR:"; then
  echo ""
  echo "   ⚠  $BIN_DIR is not in your \$PATH."
  echo "      Add this line to your ~/.bashrc or ~/.zshrc:"
  echo "        export PATH=\"\$HOME/.local/bin:\$PATH\""
  echo ""
fi

echo "==> Installing flint-ir Python package (optional)"
if command -v pipx >/dev/null 2>&1; then
  pipx install "git+${REPO_URL}" || pipx install --force "git+${REPO_URL}" || true
elif command -v pip >/dev/null 2>&1; then
  pip install --user "git+${REPO_URL}" || true
else
  echo "   (skipping — install pipx or pip to get the \`flint\` CLI)"
fi

echo ""
echo "✓ Flint installed."
echo ""
echo "Slash commands (opt-in, per turn):"
echo "  /flint <question>          one-shot: answer in strict Flint IR"
echo "  /flint-on                   turn on strict Flint for this conversation"
echo "  /flint-off                  turn off Flint mode"
echo "  /flint-audit <file|text>   decode a Flint document into readable prose"
echo ""
echo "Output-styles (opt-in, per session, set via /config):"
echo "  flint           strict IR always (best for API, parser-strict tooling)"
echo "  flint-thinking  dual-mode: Caveman prose + IR by task shape (Claude Code soft layer)"
echo ""
echo "Always-on for Claude Code Max users (recommended):"
echo "  cccflint                   starts Claude Code with Flint thinking-mode injected at"
echo "                             system-prompt level (does not affect the default 'claude')"
echo "  cccflint -p \"your prompt\"  non-interactive mode"
echo ""
echo "The default 'claude' command remains untouched — cccflint is a separate binary."
