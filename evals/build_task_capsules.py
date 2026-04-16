from __future__ import annotations

import argparse
from pathlib import Path

from sigil.task_capsule import build_capsule_task_row, dump_jsonl, load_jsonl


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build deterministic local task capsules for SIGIL evals.")
    parser.add_argument("source", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--style", choices=["v1", "micro", "nano", "bridge"], default="v1")
    args = parser.parse_args(argv)

    rows = load_jsonl(args.source)
    capsule_rows = [build_capsule_task_row(row, style=args.style) for row in rows]
    dump_jsonl(args.out, capsule_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
