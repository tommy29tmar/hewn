#!/usr/bin/env bash
# Legacy helper: rerun only the `flint-mcp` cell of the 4-cell bench.
# Other cells may already have stable data from earlier runs.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CORPUS="${CORPUS:-evals/claude_code_max_multiturn.jsonl}"
OUT_DIR="${OUT_DIR:-evals/runs/claude_code_max_4cell}"
RUNS="${RUNS:-3}"
FLINT_MCP_BIN="${FLINT_MCP_BIN:-${CCCFLINT_MCP_PRO:-$ROOT/integrations/claude-code/bin/flint-mcp}}"

mkdir -p "$OUT_DIR"

for i in $(seq 1 "$RUNS"); do
  out_file="$OUT_DIR/flint_mcp_r${i}.jsonl"
  rm -f "$out_file"
  echo "[flint-mcp r$i] starting" >&2
  python3 - "$FLINT_MCP_BIN" "$out_file" "$CORPUS" <<'PY'
import json, subprocess, sys, time
cmd = sys.argv[1]
out_path = sys.argv[2]
corpus_path = sys.argv[3]
scenarios = [json.loads(l) for l in open(corpus_path) if l.strip()]
with open(out_path, "w") as f:
    for scen in scenarios:
        sid = None
        for turn in scen["turns"]:
            tid = turn["id"]
            prompt = turn["prompt"] + ("\n\n[BENCH MODE] Do not use any tools except mcp__flint__submit_flint_ir if IR-shape. No Bash, Read, Write, Edit, Grep, Glob, Task, ToolSearch, or other MCP tools. Answer with text only (or the flint tool).")
            args = [cmd, "-p", "--output-format", "stream-json",
                    "--include-partial-messages", "--verbose"]
            if sid:
                args += ["--resume", sid]
            args += ["--", prompt]
            t0 = time.time()
            result = subprocess.run(args, capture_output=True, text=True, timeout=600)
            elapsed_ms = (time.time() - t0) * 1000
            tool_uses, usage, session_id, final_msg = [], {}, None, None
            for line in (result.stdout or "").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except:
                    continue
                if e.get("type") == "system" and e.get("subtype") == "init":
                    session_id = e.get("session_id")
                if e.get("type") == "result":
                    final_msg = e.get("result") or ""
                    usage = e.get("usage") or {}
                    if e.get("session_id"):
                        session_id = e["session_id"]
                if e.get("type") == "assistant":
                    for b in (e.get("message") or {}).get("content", []):
                        if b.get("type") == "tool_use":
                            tool_uses.append({"name": b.get("name"), "input": b.get("input") or {}})
            if session_id:
                sid = session_id
            row = {
                "scenario_id": scen["scenario_id"], "turn_id": tid,
                "variant": "flint-mcp", "session_id": sid,
                "content": final_msg or "",
                "tool_uses": tool_uses, "usage": usage,
                "elapsed_ms": elapsed_ms, "exit_code": result.returncode,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            flint = sum(1 for tu in tool_uses if "submit_flint_ir" in (tu.get("name") or "").lower())
            agent = sum(1 for tu in tool_uses if tu.get("name") and "submit_flint_ir" not in tu.get("name").lower() and tu.get("name") != "ToolSearch")
            out_tok = usage.get("output_tokens", 0)
            print(f"  {scen['scenario_id']}/{tid}: exit={result.returncode} out={out_tok} flint={flint} agent={agent}", file=sys.stderr)
PY
  echo "[flint-mcp r$i] done" >&2
done

echo ""
echo "Aggregate (4-cell table):"
python3 scripts/claude_code_max_4cell_table.py
