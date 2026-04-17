#!/usr/bin/env bash
# Stress bench: realistic long-context coding session (cache_prefix ~10k tokens).
# Compares text-sigil vs flint5-tool where the Anthropic prompt cache actually
# activates (input >4k tokens required for Opus 4.7).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODEL="claude-opus-4-7"
TASKS="evals/tasks_stress_coding.jsonl"
PROMPT="integrations/claude-code/flint_system_prompt.txt"
OUT_DIR="evals/runs/stress"
RUNS="${RUNS:-2}"

mkdir -p "$OUT_DIR"

# Sigil (text) cells — prompt cache on system AND task prefix.
for i in $(seq 1 "$RUNS"); do
  out="$OUT_DIR/opus47_stress_sigil_r${i}.jsonl"
  rm -f "$out"
  echo "[sigil run $i/$RUNS] -> $out" >&2
  python3 evals/run_anthropic.py \
    --tasks "$TASKS" \
    --model "$MODEL" \
    --out "$out" \
    --variant "sigil-stress@sigil=${PROMPT}" \
    --max-output-tokens 512 \
    --max-retries 3 \
    --cache-system-prompt \
    --cache-task-prefix \
    > "$OUT_DIR/opus47_stress_sigil_r${i}.log" 2>&1
done

# Flint5-tool cells — tool schema + cache_prefix already cached.
for i in $(seq 1 "$RUNS"); do
  out="$OUT_DIR/opus47_stress_tool_r${i}.jsonl"
  rm -f "$out"
  echo "[tool run $i/$RUNS] -> $out" >&2
  python3 evals/run_anthropic.py \
    --tasks "$TASKS" \
    --model "$MODEL" \
    --out "$out" \
    --variant "sigil-stress@flint5-tool=${PROMPT}" \
    --max-output-tokens 512 \
    --max-retries 3 \
    --cache-task-prefix \
    > "$OUT_DIR/opus47_stress_tool_r${i}.log" 2>&1
done

echo "done: 2 cells x $RUNS runs"
