from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sigil.context_prefix import compile_context_prefix, load_context_prefix
from sigil.task_capsule import load_jsonl


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build macro tasks with a compiled shared context prefix instead of the raw handbook."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("prefix", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--context-style", choices=["cacheable", "focused", "targeted"], default="cacheable")
    parser.add_argument("--task-label", default="Task")
    args = parser.parse_args(argv)

    prefix_text = load_context_prefix(args.prefix)
    source_rows = load_jsonl(args.source)
    rendered_rows: list[str] = []
    for row in source_rows:
        prompt_suffix = str(row["prompt"]).strip()
        category = str(row.get("category") or "unknown")
        compiled_prefix = compile_context_prefix(prefix_text, category=category, style=args.context_style, task=row)
        combined_prompt = f"{compiled_prefix}\n\n[{args.task_label}]\n{prompt_suffix}"
        updated = dict(row)
        updated["prompt_suffix"] = prompt_suffix
        updated["cache_prefix"] = compiled_prefix
        updated["prompt"] = combined_prompt
        updated["benchmark_scale"] = f"macro-{args.context_style}"
        updated["context_style"] = args.context_style
        rendered_rows.append(json.dumps(updated, ensure_ascii=False))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(rendered_rows) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
