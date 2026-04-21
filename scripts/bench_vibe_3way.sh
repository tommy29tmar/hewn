#!/usr/bin/env bash
# Vibe-coding bench: 8 open-ended prompts x 3 wrappers, parallel per-prompt.
# Tools ENABLED (that's the vibe-coding point).

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CORPUS="${CORPUS:-evals/vibe_3way.jsonl}"
OUT_DIR="${OUT_DIR:-evals/runs/vibe_3way}"
MAX_CONCURRENCY="${MAX_CONCURRENCY:-6}"

mkdir -p "$OUT_DIR"

run_one() {
  local variant="$1" cmd="$2" prompt_id="$3" prompt="$4"
  local out_file="$OUT_DIR/${variant}_${prompt_id}.json"
  python3 - "$cmd" "$out_file" "$prompt_id" "$prompt" "$variant" <<'PY'
import json, subprocess, sys, time
cmd, out_path, prompt_id, prompt, variant = sys.argv[1:6]
# BENCH MODE: no subagents. Agent/Task delegate tool work that doesn't
# show in parent tool_uses/usage — inflates quality asymmetrically.
bench_suffix = "\n\n[BENCH MODE] Do not use Agent or Task subagent tools. Do all work inline with Read/Grep/Glob/Bash. No delegation."
prompt_with_suffix = prompt + bench_suffix
args = cmd.split() + ["-p", "--output-format", "stream-json",
                       "--include-partial-messages", "--verbose", "--", prompt_with_suffix]
t0 = time.time()
result = subprocess.run(args, capture_output=True, text=True, timeout=600)
elapsed_ms = (time.time() - t0) * 1000
tool_uses = []
usage = {}
final_msg = None
for line in (result.stdout or "").splitlines():
    line = line.strip()
    if not line:
        continue
    try:
        e = json.loads(line)
    except Exception:
        continue
    if e.get("type") == "result":
        final_msg = e.get("result") or ""
        usage = e.get("usage") or {}
    if e.get("type") == "assistant":
        for b in (e.get("message") or {}).get("content", []):
            if b.get("type") == "tool_use":
                tool_uses.append({"name": b.get("name"), "input": b.get("input") or {}})
row = {
    "variant": variant,
    "prompt_id": prompt_id,
    "prompt": prompt,
    "content": final_msg or "",
    "tool_uses": tool_uses,
    "usage": usage,
    "elapsed_ms": elapsed_ms,
    "exit_code": result.returncode,
}
with open(out_path, "w") as f:
    json.dump(row, f, ensure_ascii=False)
tcount = len(tool_uses)
ot = usage.get("output_tokens", 0)
print(f"  [{variant}] {prompt_id}: out={ot} tools={tcount} exit={result.returncode}", file=sys.stderr)
PY
}
export -f run_one
export OUT_DIR

# Build job list: variant|cmd|prompt_id|prompt
JOBS=$(python3 -c "
import json
rows = [json.loads(l) for l in open('$CORPUS') if l.strip()]
variants = [('plain','claude'), ('cccaveman','cccaveman'), ('flint','flint')]
for r in rows:
    for name, cmd in variants:
        print(f\"{name}|{cmd}|{r['id']}|{r['prompt']}\")
")

# Launch parallel, bounded
echo "$JOBS" | xargs -I{} -d '\n' -P "$MAX_CONCURRENCY" bash -c '
  IFS="|" read -r name cmd pid prompt <<< "{}"
  echo "[${name} ${pid}] start" >&2
  run_one "$name" "$cmd" "$pid" "$prompt"
  echo "[${name} ${pid}] done" >&2
'

echo "" >&2
echo "Done. Aggregate with scripts/vibe_3way_table.py" >&2
