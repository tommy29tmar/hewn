#!/usr/bin/env bash
# Realistic long-context bench: verbose vs Caveman vs Flint.
# Uses tasks with ~10k tokens of project-handbook cache_prefix (simulating
# a real Claude Code / RAG / agent session where prompt cache is active).
# This is Flint's best-case scenario and the one that actually reflects
# production usage — the short-prompt micro bench under-sells Flint.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODEL="${MODEL:-claude-opus-4-7}"
TASKS="evals/tasks_stress_coding.jsonl"
OUT_DIR="evals/runs/stress"
RUNS="${RUNS:-2}"
mkdir -p "$OUT_DIR"

run_cell() {
  local name="$1" transport="$2" ppath="$3" idx="$4"
  local max_tokens="$5"
  local out="$OUT_DIR/opus47_stress_${name}_r${idx}.jsonl"
  rm -f "$out"
  echo "[$name r$idx] start" >&2
  python3 evals/run_anthropic.py \
    --tasks "$TASKS" \
    --model "$MODEL" \
    --out "$out" \
    --variant "${name}-stress@${transport}=${ppath}" \
    --max-output-tokens "$max_tokens" \
    --max-retries 3 \
    --cache-system-prompt --cache-task-prefix \
    > "$OUT_DIR/opus47_stress_${name}_r${idx}.log" 2>&1
  echo "[$name r$idx] done" >&2
}

for i in $(seq 1 "$RUNS"); do
  run_cell "verbose"  "plain" "prompts/verbose_baseline.txt"                            "$i" 1024 &
  run_cell "caveman"  "plain" "prompts/primitive_english.txt"                           "$i"  512 &
  run_cell "flintnew" "sigil" "integrations/claude-code/flint_system_prompt.txt"        "$i"  512 &
  run_cell "flintthinking" "plain" "integrations/claude-code/flint_thinking_system_prompt.txt" "$i"  512 &
done
wait
echo "all stress cells done (${RUNS} run(s) per cell)"
echo ""
echo "Aggregate table:"
python3 scripts/stress_table.py
