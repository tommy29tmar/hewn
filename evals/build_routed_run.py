from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            rows.append(json.loads(stripped))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_number}: invalid JSONL row: {exc}") from exc
    return rows


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compose a routed SIGIL benchmark run from multiple source run files.")
    parser.add_argument("tasks", type=Path, help="Task JSONL file.")
    parser.add_argument("profile", type=Path, help="Routing profile JSON file.")
    parser.add_argument("out", type=Path, help="Output JSONL path.")
    parser.add_argument(
        "--source-run",
        dest="source_runs",
        action="append",
        type=Path,
        required=True,
        help="Run JSONL file to source variants from. Repeatable.",
    )
    parser.add_argument("--variant-name", default="sigil-routed", help="Variant name to assign to routed selections.")
    parser.add_argument("--baseline-run", type=Path, default=None, help="Optional run file containing baseline rows.")
    parser.add_argument("--baseline-variant", default="baseline-terse", help="Variant name to copy from the baseline run.")
    args = parser.parse_args(argv)

    tasks = load_jsonl(args.tasks)
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    categories = profile.get("categories") or {}
    task_overrides = profile.get("tasks") or {}
    if not isinstance(categories, dict) or not categories:
        if not isinstance(task_overrides, dict) or not task_overrides:
            raise SystemExit("Routing profile must contain a non-empty 'categories' or 'tasks' mapping.")

    rows_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for run_path in args.source_runs:
        for row in load_jsonl(run_path):
            rows_by_key[(str(row["task_id"]), str(row["variant"]))] = row

    output_rows: list[dict[str, Any]] = []
    baseline_rows_by_key: dict[tuple[str, str], dict[str, Any]] = {}

    if args.baseline_run is not None:
        baseline_rows = load_jsonl(args.baseline_run)
        for row in baseline_rows:
            baseline_rows_by_key[(str(row["task_id"]), str(row["variant"]))] = row
        for task in tasks:
            task_id = str(task["id"])
            matched = baseline_rows_by_key.get((task_id, args.baseline_variant))
            if matched is None:
                raise SystemExit(f"Missing baseline row for task '{task_id}' and variant '{args.baseline_variant}'.")
            output_rows.append(matched)

    for task in tasks:
        task_id = str(task["id"])
        category = str(task.get("category"))
        selected_variant = task_overrides.get(task_id) or categories.get(category)
        if not selected_variant:
            raise SystemExit(f"No routed variant configured for task '{task_id}' or category '{category}'.")
        source_row = rows_by_key.get((task_id, str(selected_variant)))
        if source_row is None and baseline_rows_by_key:
            source_row = baseline_rows_by_key.get((task_id, str(selected_variant)))
        if source_row is None:
            raise SystemExit(f"Missing source row for task '{task_id}' and variant '{selected_variant}'.")
        routed_row = dict(source_row)
        routed_row["variant"] = args.variant_name
        routed_row["policy_name"] = profile.get("name", args.variant_name)
        routed_row["policy_source_variant"] = selected_variant
        output_rows.append(routed_row)

    append_jsonl(args.out, output_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
