from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        rows.append(json.loads(stripped))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Expand tasks with a long reusable cache prefix for macro benchmark runs.")
    parser.add_argument("source", type=Path)
    parser.add_argument("prefix", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--task-label", default="Task")
    args = parser.parse_args(argv)

    prefix_text = args.prefix.read_text(encoding="utf-8").strip()
    source_rows = load_jsonl(args.source)
    rendered_rows: list[str] = []
    for row in source_rows:
        prompt_suffix = str(row["prompt"]).strip()
        combined_prompt = f"{prefix_text}\n\n[{args.task_label}]\n{prompt_suffix}"
        updated = dict(row)
        updated["prompt_suffix"] = prompt_suffix
        updated["cache_prefix"] = prefix_text
        updated["prompt"] = combined_prompt
        updated["benchmark_scale"] = "macro"
        rendered_rows.append(json.dumps(updated, ensure_ascii=False))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(rendered_rows) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
