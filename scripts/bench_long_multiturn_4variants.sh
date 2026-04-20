#!/usr/bin/env bash
# Long multi-turn bench: 4 variants on 3 long scenarios (16 turns each run).
# Compares compression + quality + latency across:
#   - plain claude (baseline)
#   - cccaveman (descriptive compression baseline)
#   - flint (thinking-mode + drift-fix hook, free-text IR)
#   - flint-mcp (thinking-mode + drift-fix hook + MCP tool enforcement)

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CORPUS="${CORPUS:-evals/claude_code_max_long_multiturn.jsonl}"
OUT_DIR="${OUT_DIR:-evals/runs/claude_code_max_long_multiturn_4var}"
RUNS="${RUNS:-2}"

mkdir -p "$OUT_DIR"

run_variant() {
  local name="$1" cmd="$2" idx="$3"
  local out_file="$OUT_DIR/${name}_r${idx}.jsonl"
  rm -f "$out_file"
  echo "[${name} r${idx}] starting" >&2
  python3 - "$cmd" "$out_file" "$CORPUS" "$name" <<'PY'
import json, subprocess, sys, time
cmd = sys.argv[1]
out_path = sys.argv[2]
corpus_path = sys.argv[3]
cell_name = sys.argv[4]
scenarios = [json.loads(l) for l in open(corpus_path) if l.strip()]

# Per-cell tool discipline (inject in-prompt; hook settings separately for pro variants)
is_mcp = "mcp" in cell_name.lower()

with open(out_path, "w") as f:
    for scen in scenarios:
        sid = None
        for turn in scen["turns"]:
            tid = turn["id"]
            if is_mcp:
                bench_suffix = "\n\n[BENCH MODE] Do not use any tools except mcp__flint__submit_flint_ir if IR-shape. No Bash, Read, Write, Edit, Grep, Glob, Task, ToolSearch, or other MCP tools. Answer with text only (or the flint tool)."
            else:
                bench_suffix = "\n\n[BENCH MODE] Do not use any tools (no Bash, Read, Write, Edit, Grep, Glob, Task, ToolSearch, MCP tools). Answer with text only."
            prompt = turn["prompt"] + bench_suffix

            args = cmd.split() + ["-p", "--output-format", "stream-json",
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
                "variant": cell_name, "session_id": sid,
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
  echo "[${name} r${idx}] done" >&2
}

for i in $(seq 1 "$RUNS"); do
  run_variant "plain"             "claude"           "$i"
  run_variant "cccaveman"         "cccaveman"        "$i"
  run_variant "flint"      "flint"     "$i"
  run_variant "flint_mcp"  "flint-mcp" "$i"
done

echo ""
echo "Done. Aggregate with claude_code_max_long_multiturn_4var_table.py"
