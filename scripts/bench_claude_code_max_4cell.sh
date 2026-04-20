#!/usr/bin/env bash
# 4-cell multi-turn bench:
#   1. plain `claude`                           (baseline Anthropic default)
#   2. `flint`                                  (Flint system prompt + drift-fix hook, no MCP)
#   3. plain `claude --mcp-config <flint>`      (MCP tool available, no system prompt push)
#   4. `flint-mcp`                              (Flint system prompt + MCP + drift-fix hook)
#
# Uses the multi-turn scenarios via --resume for session continuity.
# Measures per-turn IR emission, tool calls, classification, tokens, latency.
# Zero Anthropic API cost (Claude Max plan).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CORPUS="${CORPUS:-evals/claude_code_max_multiturn.jsonl}"
OUT_DIR="${OUT_DIR:-evals/runs/claude_code_max_4cell}"
RUNS="${RUNS:-1}"
FLINT_BIN="${FLINT_BIN:-${CCCFLINT:-$ROOT/integrations/claude-code/bin/flint}}"
FLINT_MCP_BIN="${FLINT_MCP_BIN:-${CCCFLINT_MCP:-$ROOT/integrations/claude-code/bin/flint-mcp}}"
MCP_CONFIG="${MCP_CONFIG:-$ROOT/integrations/claude-code/mcp-config.json}"

export FLINT_THINKING_PROMPT_FILE="$ROOT/integrations/claude-code/flint_thinking_system_prompt.txt"
export FLINT_THINKING_MCP_PROMPT_FILE="$ROOT/integrations/claude-code/flint_thinking_mcp_system_prompt.txt"
export FLINT_MCP_CONFIG_FILE="$MCP_CONFIG"

mkdir -p "$OUT_DIR"

# Four cells: name, command-string, extra-args
run_cell() {
  local name="$1" cmd="$2" idx="$3" extra="${4:-}"
  local out_file="$OUT_DIR/${name}_r${idx}.jsonl"
  rm -f "$out_file"
  echo "[${name} r${idx}] starting" >&2
  python3 - "$cmd" "$out_file" "$CORPUS" "$extra" <<'PY'
import json, shlex, subprocess, sys, time
cmd = sys.argv[1]
out_path = sys.argv[2]
corpus_path = sys.argv[3]
extra_args = shlex.split(sys.argv[4]) if sys.argv[4] else []
scenarios = [json.loads(l) for l in open(corpus_path) if l.strip()]

with open(out_path, "w") as out_f:
    for scen in scenarios:
        sid = None
        for turn in scen["turns"]:
            tid = turn["id"]
            prompt = turn["prompt"]
            # Cell-specific tool discipline. Plain and flint cells must not
            # use any tools (otherwise agent behavior inflates out_tok with tool
            # round-trips). MCP cells may call the Flint MCP tool but nothing
            # else. The CLI --disallowedTools flag is bypassable via MCP tools,
            # so we ALSO instruct the model in-prompt. This is the reliable way.
            if "mcp" in out_path.lower():
                discipline = ("\n\n[BENCH MODE] Do not use any tools except "
                              "`mcp__flint__submit_flint_ir` if IR-shape. No Bash, Read, "
                              "Write, Edit, Grep, Glob, Task, ToolSearch, or other MCP tools. "
                              "Answer with text only (or the flint tool).")
            else:
                discipline = ("\n\n[BENCH MODE] Do not use any tools (no Bash, Read, Write, "
                              "Edit, Grep, Glob, Task, ToolSearch, MCP tools). Answer with text only.")
            prompt = prompt + discipline
            args = cmd.split() + ["-p", "--output-format", "stream-json",
                                   "--include-partial-messages", "--verbose"] + extra_args
            if sid:
                args += ["--resume", sid]
            # -- terminates variadic flags (--mcp-config) before positional prompt
            args += ["--", prompt]
            t0 = time.time()
            try:
                result = subprocess.run(args, capture_output=True, text=True, timeout=600)
                elapsed_ms = (time.time() - t0) * 1000
                # Parse stream-json: one JSON object per line
                tool_uses = []
                content_blocks = []
                usage = {}
                session_id = None
                final_message = None
                for line in (result.stdout or "").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        evt = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if evt.get("type") == "system" and evt.get("subtype") == "init":
                        session_id = evt.get("session_id")
                    if evt.get("type") == "result":
                        final_message = evt.get("result") or ""
                        usage = evt.get("usage") or {}
                        if evt.get("session_id"):
                            session_id = evt["session_id"]
                    if evt.get("type") == "assistant":
                        msg = evt.get("message") or {}
                        for block in msg.get("content", []):
                            btype = block.get("type")
                            if btype == "tool_use":
                                tool_uses.append({
                                    "name": block.get("name"),
                                    "input": block.get("input") or {},
                                })
                            elif btype == "text":
                                t = block.get("text")
                                if t:
                                    content_blocks.append(t)
                if session_id:
                    sid = session_id
                row = {
                    "scenario_id": scen["scenario_id"],
                    "turn_id": tid,
                    "variant": cmd + (" " + " ".join(extra_args) if extra_args else ""),
                    "session_id": sid,
                    "content": final_message if final_message is not None else "\n".join(content_blocks),
                    "tool_uses": tool_uses,
                    "usage": usage,
                    "elapsed_ms": elapsed_ms,
                    "exit_code": result.returncode,
                }
            except subprocess.TimeoutExpired:
                row = {"scenario_id": scen["scenario_id"], "turn_id": tid, "variant": cmd, "error": "timeout"}
            except Exception as e:
                row = {"scenario_id": scen["scenario_id"], "turn_id": tid, "variant": cmd, "error": str(e)}
            out_f.write(json.dumps(row, ensure_ascii=False) + "\n")
            out_f.flush()
            flint_tool_calls = sum(1 for tu in row.get("tool_uses", []) if "flint" in (tu.get("name") or "").lower())
            print(f"  [{scen['scenario_id']}/{tid}] done (sid={sid[:8] if sid else '?'}, tool_calls_flint={flint_tool_calls})", file=sys.stderr)
PY
  echo "[${name} r${idx}] done → $out_file" >&2
}

for i in $(seq 1 "$RUNS"); do
  run_cell "plain"      "claude"         "$i" ""
  run_cell "flint"      "$FLINT_BIN"     "$i" ""
  run_cell "plain_mcp"  "claude"         "$i" "--mcp-config $MCP_CONFIG"
  run_cell "flint_mcp"  "$FLINT_MCP_BIN" "$i" ""
done

echo ""
echo "Aggregate:"
python3 scripts/claude_code_max_4cell_table.py
