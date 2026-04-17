#!/usr/bin/env bash
# Head-to-head SIGIL vs Caveman (primitive-english) vs concise+JSON control vs verbose Claude.
# Same frame Caveman uses to report "~60% savings". Run ${RUNS:-4} times per cell
# so the aggregate table has confidence intervals, not single-shot noise.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODEL="claude-opus-4-7"
TASKS="evals/tasks_top_tier_holdout.jsonl"
OUT_DIR="evals/runs/caveman"
RUNS="${RUNS:-4}"
mkdir -p "$OUT_DIR"

run_cell() {
  local name="$1" transport="$2" ppath="$3" idx="$4"
  local suffix=""
  [ "$idx" != "0" ] && suffix="_r${idx}"
  local out="$OUT_DIR/opus47_${name}${suffix}.jsonl"
  rm -f "$out"
  echo "[$name run=$idx] start" >&2
  python3 evals/run_anthropic.py \
    --tasks "$TASKS" \
    --model "$MODEL" \
    --out "$out" \
    --variant "${name}${suffix}@${transport}=${ppath}" \
    --max-output-tokens 1024 \
    --max-retries 3 \
    > "$OUT_DIR/opus47_${name}${suffix}.log" 2>&1
  echo "[$name run=$idx] done" >&2
}

for i in $(seq 1 "$RUNS"); do
  run_cell "verbose"      "plain"  "prompts/verbose_baseline.txt" "$i" &
  run_cell "primitive"    "plain"  "prompts/primitive_english.txt" "$i" &
  run_cell "concise_json" "plain"  "prompts/concise_json.txt" "$i" &
  run_cell "sigil"        "sigil"  "integrations/claude-code/flint_system_prompt.txt" "$i" &
done
wait
echo "all cells done (${RUNS} run(s) per cell)"
echo ""
echo "Aggregate table:"
python3 scripts/caveman_table.py
