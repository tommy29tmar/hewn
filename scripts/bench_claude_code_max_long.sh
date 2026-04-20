#!/usr/bin/env bash
# Claude Code Max bench: plain `claude -p` vs `flint -p` on 6 fixed prompts.
# Uses the user's Claude Max plan (not Anthropic API), so cost is $0 marginal.
#
# Usage:
#   ./scripts/bench_claude_code_max_long.sh           # runs both variants, 1 run each
#   RUNS=3 ./scripts/bench_claude_code_max_long.sh    # 3 runs per variant per prompt
#
# Output:
#   evals/runs/claude_code_max_long/{plain,flint}_r<i>.jsonl

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CORPUS="${CORPUS:-evals/claude_code_max_long_prompts.jsonl}"
OUT_DIR="${OUT_DIR:-evals/runs/claude_code_max_long}"
RUNS="${RUNS:-1}"
FLINT_BIN="${FLINT_BIN:-${CCCFLINT:-$ROOT/integrations/claude-code/bin/flint}}"

# Ensure flint can find the prompt file even if not installed globally
export FLINT_THINKING_PROMPT_FILE="$ROOT/integrations/claude-code/flint_thinking_system_prompt.txt"

mkdir -p "$OUT_DIR"

run_variant() {
  local name="$1" cmd="$2" idx="$3"
  local out_file="$OUT_DIR/${name}_r${idx}.jsonl"
  rm -f "$out_file"
  echo "[${name} r${idx}] starting" >&2
  python3 - "$cmd" "$out_file" <<'PY'
import json, subprocess, sys, time
cmd = sys.argv[1]
out_path = sys.argv[2]
corpus = [json.loads(l) for l in open("evals/claude_code_max_long_prompts.jsonl") if l.strip()]
with open(out_path, "w") as f:
    for task in corpus:
        tid = task["id"]
        prompt = task["prompt"]
        # Use --output-format json for structured result with usage.
        args = cmd.split() + ["-p", "--output-format", "json", prompt]
        t0 = time.time()
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=300)
            elapsed_ms = (time.time() - t0) * 1000
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            parsed = None
            content = ""
            usage = {}
            if stdout:
                try:
                    parsed = json.loads(stdout)
                    # Claude Code JSON print format:
                    # {"type": "result", "subtype": "success", "result": "text...", "usage": {...}, ...}
                    if isinstance(parsed, dict):
                        content = parsed.get("result") or parsed.get("content") or ""
                        usage = parsed.get("usage") or {}
                except json.JSONDecodeError:
                    content = stdout  # fallback: treat raw stdout as response
            row = {
                "task_id": tid,
                "variant": sys.argv[1],
                "content": content,
                "usage": usage,
                "elapsed_ms": elapsed_ms,
                "exit_code": result.returncode,
                "stderr_tail": stderr[-500:] if stderr else "",
            }
        except subprocess.TimeoutExpired:
            row = {"task_id": tid, "variant": cmd, "error": "timeout"}
        except Exception as e:
            row = {"task_id": tid, "variant": cmd, "error": str(e)}
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        print(f"  [{tid}] done", file=sys.stderr)
PY
  echo "[${name} r${idx}] done → $out_file" >&2
}

for i in $(seq 1 "$RUNS"); do
  run_variant "plain"  "claude"       "$i"
  run_variant "flint"  "$FLINT_BIN"   "$i"
done

echo ""
echo "Aggregate table:"
python3 scripts/claude_code_max_long_table.py
