#!/usr/bin/env bash
# Hewn — Claude Code installer.
#
# One-line install:
#   curl -fsSL https://raw.githubusercontent.com/tommy29tmar/hewn/main/integrations/claude-code/install.sh | bash
#
# Installs:
#   - hewn CLI wrapper to ~/.local/bin/hewn
#   - hewn_thinking_system_prompt.txt to ~/.claude/
#   - hewn_drift_fixer.py UserPromptSubmit hook to ~/.claude/hooks/
#
# Refuses to run if ~/.claude is not present (i.e. Claude Code not installed).

set -euo pipefail

CLAUDE_DIR="${HOME}/.claude"
BIN_DIR="${HOME}/.local/bin"
# TODO: switch to tommy29tmar/hewn after the GitHub repo rename lands; GitHub
# auto-redirects the old URL during the transition.
REPO_URL="https://github.com/tommy29tmar/flint.git"
RAW_URL="https://raw.githubusercontent.com/tommy29tmar/flint/main"

if [ ! -d "$CLAUDE_DIR" ]; then
  echo "error: ~/.claude not found. Install Claude Code first."
  exit 1
fi

# Local-checkout detection: checks a file that survives the install.
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"
fi
IS_LOCAL=0
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/bin/hewn" ]; then
  IS_LOCAL=1
fi

fetch() {
  local rel="$1"; local dest="$2"
  if [ "$IS_LOCAL" = "1" ]; then
    cp "$SCRIPT_DIR/$rel" "$dest"
  else
    curl -fsSL "$RAW_URL/integrations/claude-code/$rel" -o "$dest"
  fi
}

mkdir -p "$BIN_DIR" "$CLAUDE_DIR/hooks"

echo "==> Installing hewn CLI wrapper"
fetch "bin/hewn" "$BIN_DIR/hewn"
chmod +x "$BIN_DIR/hewn"

echo "==> Installing hewn thinking-mode system prompt"
fetch "hewn_thinking_system_prompt.txt" "$CLAUDE_DIR/hewn_thinking_system_prompt.txt"

echo "==> Installing drift-fix hook"
fetch "hooks/hewn_drift_fixer.py" "$CLAUDE_DIR/hooks/hewn_drift_fixer.py"
chmod +x "$CLAUDE_DIR/hooks/hewn_drift_fixer.py"

if ! echo ":$PATH:" | grep -q ":$BIN_DIR:"; then
  echo ""
  echo "⚠  $BIN_DIR is not on your \$PATH. Add this to your shell rc:"
  echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo ""
echo "✓ Hewn installed."
echo ""
echo "Usage:"
echo "  hewn                     start Claude Code with Hewn thinking-mode + drift-fix hook"
echo "  hewn -p \"your prompt\"    non-interactive mode"
echo ""
echo "The default 'claude' command is untouched — hewn is a separate binary."
echo ""
echo "If you previously installed Flint, clean up legacy files:"
echo "  rm -rf \\"
echo "    ~/.claude/skills/flint ~/.claude/skills/flint-on \\"
echo "    ~/.claude/skills/flint-off ~/.claude/skills/flint-audit \\"
echo "    ~/.claude/output-styles/flint.md ~/.claude/output-styles/flint-thinking.md \\"
echo "    ~/.claude/output-styles/hewn.md ~/.claude/output-styles/hewn-thinking.md \\"
echo "    ~/.claude/flint_thinking_system_prompt.txt \\"
echo "    ~/.claude/flint_thinking_mcp_system_prompt.txt \\"
echo "    ~/.claude/flint_system_prompt.txt \\"
echo "    ~/.claude/flint-drift-fix-settings.json \\"
echo "    ~/.claude/flint-mcp-config.json \\"
echo "    ~/.claude/hooks/flint_drift_fixer.py"
echo "  rm -f ~/.local/bin/flint ~/.local/bin/flint-mcp \\"
echo "        ~/.local/bin/hewn-mcp ~/.local/bin/cccaveman"
