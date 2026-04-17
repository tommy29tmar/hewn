#!/usr/bin/env python3
"""Build a stress-test task file that simulates a realistic long coding session.

Takes tasks_hybrid_macro.jsonl as seed and inflates cache_prefix to ~7k tokens
by appending real project content (Flint manifesto + breakthroughs + calibration
docs). The resulting total input per task (~7-8k tokens) is well above the
Opus 4.7 cache threshold of 4096, so prompt caching activates.

Writes evals/tasks_stress_coding.jsonl.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "evals" / "tasks_hybrid_macro.jsonl"
OUT = ROOT / "evals" / "tasks_stress_coding.jsonl"

# Additional realistic project docs — concat to cache_prefix to push above 4k.
PAD_SOURCES = [
    ROOT / "docs" / "manifesto.md",
    ROOT / "docs" / "breakthroughs.md",
    ROOT / "docs" / "calibration.md",
]


def build_padding() -> str:
    chunks = ["\n\n# Additional project context (reference material)\n"]
    for src in PAD_SOURCES:
        chunks.append(f"\n\n## Reference: {src.name}\n\n")
        chunks.append(src.read_text(encoding="utf-8"))
    return "".join(chunks)


def main() -> int:
    padding = build_padding()
    rows = []
    for line in SEED.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        row["cache_prefix"] = row["cache_prefix"] + padding
        # Keep prompt_suffix as the capsule (short) — that's what gets sent as user msg.
        # Drop the prompt field's legacy embedded handbook (not used when --cache-task-prefix).
        row["benchmark_scale"] = "stress"
        rows.append(row)
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # Report sizes
    for r in rows:
        print(
            f"  {r['id']:<30} cache_prefix={len(r['cache_prefix']):>6} chars "
            f"(~{len(r['cache_prefix']) // 4} tok), suffix={len(r['prompt_suffix'])} chars",
            file=sys.stderr,
        )
    print(f"wrote {OUT} ({len(rows)} rows)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
