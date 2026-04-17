#!/usr/bin/env bash
# Run the full 3-way launch benchmark for one model.
# Usage: ./run_launch_bench.sh <model> <short_id>
set -euo pipefail

MODEL="${1}"
SHORT="${2}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TASKS="evals/tasks_top_tier_holdout.jsonl"
OUT_DIR="evals/runs/launch"
mkdir -p "$OUT_DIR"

echo "[$SHORT] === baseline-terse ==="
python3 scripts/bench_cell.py \
  --model "$MODEL" \
  --variant "baseline-terse@plain=prompts/baseline_terse.txt" \
  --tasks "$TASKS" \
  --out "$OUT_DIR/${SHORT}_terse.jsonl" \
  --start-max-tokens 512 \
  --max-retries 3

echo "[$SHORT] === primitive-english ==="
python3 scripts/bench_cell.py \
  --model "$MODEL" \
  --variant "primitive-english@plain=prompts/primitive_english.txt" \
  --tasks "$TASKS" \
  --out "$OUT_DIR/${SHORT}_primitive.jsonl" \
  --start-max-tokens 512 \
  --max-retries 3

echo "[$SHORT] === sigil-nano ==="
python3 scripts/bench_cell.py \
  --model "$MODEL" \
  --variant "sigil-nano@sigil=integrations/claude-code/flint_system_prompt.txt" \
  --tasks "$TASKS" \
  --out "$OUT_DIR/${SHORT}_sigil.jsonl" \
  --start-max-tokens 512 \
  --max-retries 3

echo "[$SHORT] === done ==="
