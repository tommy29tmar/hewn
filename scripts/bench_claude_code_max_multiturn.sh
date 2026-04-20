#!/usr/bin/env bash
# Multi-turn bench: plain `claude` vs `flint` across session-persistent
# conversations. Each scenario runs 4 turns via --resume <session_id> to
# preserve context. Measures per-turn classification, parser-pass, tokens,
# and cumulative compression across the full session.
#
# Uses the user's Claude Max plan (zero Anthropic API cost).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CORPUS="${CORPUS:-evals/claude_code_max_multiturn.jsonl}"
OUT_DIR="${OUT_DIR:-evals/runs/claude_code_max_multiturn}"
RUNS="${RUNS:-1}"
FLINT_BIN="${FLINT_BIN:-${CCCFLINT:-$ROOT/integrations/claude-code/bin/flint}}"

export FLINT_THINKING_PROMPT_FILE="$ROOT/integrations/claude-code/flint_thinking_system_prompt.txt"

mkdir -p "$OUT_DIR"

run_variant() {
  local name="$1" cmd="$2" idx="$3"
  local out_file="$OUT_DIR/${name}_r${idx}.jsonl"
  rm -f "$out_file"
  echo "[${name} r${idx}] starting" >&2
  python3 - "$cmd" "$out_file" "$CORPUS" <<'PY'
import json, subprocess, sys, time
cmd = sys.argv[1]
out_path = sys.argv[2]
corpus_path = sys.argv[3]
scenarios = [json.loads(l) for l in open(corpus_path) if l.strip()]

with open(out_path, "w") as out_f:
    for scen in scenarios:
        sid = None  # session id returned by claude, used for --resume
        for turn in scen["turns"]:
            tid = turn["id"]
            prompt = turn["prompt"]
            args = cmd.split() + ["-p", "--output-format", "json"]
            if sid:
                args += ["--resume", sid]
            args.append(prompt)
            t0 = time.time()
            try:
                result = subprocess.run(args, capture_output=True, text=True, timeout=420)
                elapsed_ms = (time.time() - t0) * 1000
                stdout = result.stdout.strip()
                parsed = None
                content, usage = "", {}
                if stdout:
                    try:
                        parsed = json.loads(stdout)
                        if isinstance(parsed, dict):
                            content = parsed.get("result") or ""
                            usage = parsed.get("usage") or {}
                            sid = parsed.get("session_id") or sid
                    except json.JSONDecodeError:
                        content = stdout
                row = {
                    "scenario_id": scen["scenario_id"],
                    "turn_id": tid,
                    "variant": cmd,
                    "session_id": sid,
                    "content": content,
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
            print(f"  [{scen['scenario_id']}/{tid}] done (sid={sid[:8] if sid else '?'}...)", file=sys.stderr)
PY
  echo "[${name} r${idx}] done → $out_file" >&2
}

for i in $(seq 1 "$RUNS"); do
  run_variant "plain" "claude"    "$i"
  run_variant "flint" "$FLINT_BIN" "$i"
done

echo ""
echo "Aggregate:"
python3 scripts/claude_code_max_multiturn_table.py
