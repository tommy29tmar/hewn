#!/usr/bin/env bash
# Parallel version of bench_long_multiturn_4variants.sh.
#
# Parallelism model:
#   - Turns within a scenario: SEQUENTIAL (--resume requires prior session_id)
#   - Scenarios within a variant: PARALLEL (independent sessions)
#   - Variants: PARALLEL (independent)
#   - Runs: PARALLEL (independent)
#
# With 3 scenarios × 4 variants × RUNS concurrent chains, max concurrency is
# 12*RUNS. Claude Max plan throttles beyond ~5-10 concurrent sessions, so
# tune via MAX_CONCURRENCY env var.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CORPUS="${CORPUS:-evals/claude_code_max_long_multiturn.jsonl}"
OUT_DIR="${OUT_DIR:-evals/runs/claude_code_max_long_multiturn_4var}"
RUNS="${RUNS:-2}"
MAX_CONCURRENCY="${MAX_CONCURRENCY:-8}"

mkdir -p "$OUT_DIR"

# Worker: runs one (variant, run, scenario) chain -> appends to ${name}_r${idx}.jsonl
run_chain() {
  local name="$1" cmd="$2" idx="$3" scen_id="$4"
  local out_file="$OUT_DIR/${name}_r${idx}.jsonl"
  local tmp_file="$OUT_DIR/.${name}_r${idx}_${scen_id}.jsonl"
  python3 - "$cmd" "$tmp_file" "$CORPUS" "$name" "$scen_id" <<'PY'
import json, subprocess, sys, time
cmd = sys.argv[1]
out_path = sys.argv[2]
corpus_path = sys.argv[3]
cell_name = sys.argv[4]
scen_id = sys.argv[5]
scenarios = [json.loads(l) for l in open(corpus_path) if l.strip()]
scen = next(s for s in scenarios if s["scenario_id"] == scen_id)
is_mcp = "mcp" in cell_name.lower()

with open(out_path, "w") as f:
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
        print(f"  [{cell_name} r{sys.argv[2].split('_r')[1].split('_')[0] if '_r' in sys.argv[2] else '?'}] {scen['scenario_id']}/{tid}: exit={result.returncode} out={out_tok} flint={flint} agent={agent}", file=sys.stderr)
PY
}

export -f run_chain
export CORPUS OUT_DIR

# Get scenario IDs from corpus
SCENARIOS=$(python3 -c "import json; [print(json.loads(l)['scenario_id']) for l in open('$CORPUS') if l.strip()]")

# Clear old partials + target files
for name in plain cccaveman flint flint_mcp; do
  for i in $(seq 1 "$RUNS"); do
    rm -f "$OUT_DIR/${name}_r${i}.jsonl"
    for scen in $SCENARIOS; do
      rm -f "$OUT_DIR/.${name}_r${i}_${scen}.jsonl"
    done
  done
done

echo "[parallel] launching up to ${MAX_CONCURRENCY} concurrent chains" >&2

# Generate all (name, cmd, run, scenario) tuples
JOBS=""
for i in $(seq 1 "$RUNS"); do
  for scen in $SCENARIOS; do
    JOBS+="plain|claude|$i|$scen"$'\n'
    JOBS+="cccaveman|cccaveman|$i|$scen"$'\n'
    JOBS+="flint|flint|$i|$scen"$'\n'
    JOBS+="flint_mcp|flint-mcp|$i|$scen"$'\n'
  done
done

# Launch with bounded concurrency using GNU xargs -P
echo "$JOBS" | grep -v '^$' | xargs -I{} -P "$MAX_CONCURRENCY" bash -c '
  IFS="|" read -r name cmd idx scen <<< "{}"
  echo "[${name} r${idx} ${scen}] start" >&2
  run_chain "$name" "$cmd" "$idx" "$scen"
  echo "[${name} r${idx} ${scen}] done" >&2
'

# Merge partials into ${name}_r${idx}.jsonl (preserve order: scenario list order)
echo "[parallel] merging partials" >&2
for name in plain cccaveman flint flint_mcp; do
  for i in $(seq 1 "$RUNS"); do
    target="$OUT_DIR/${name}_r${i}.jsonl"
    : > "$target"
    for scen in $SCENARIOS; do
      part="$OUT_DIR/.${name}_r${i}_${scen}.jsonl"
      if [ -f "$part" ]; then
        cat "$part" >> "$target"
        rm "$part"
      fi
    done
  done
done

echo ""
echo "Done. Aggregate with claude_code_max_long_multiturn_4var_table.py"
