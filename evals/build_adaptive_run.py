from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flint.eval_common import load_jsonl
from flint.verification import assess_output, verification_failures


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def index_rows(run_paths: list[Path]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for run_path in run_paths:
        for row in load_jsonl(run_path):
            task_id = str(row["task_id"])
            if task_id in indexed:
                raise SystemExit(f"Duplicate task_id '{task_id}' across supplied run files.")
            indexed[task_id] = row
    return indexed


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, int] = {}
    for row in rows:
        variant = str(row["variant"])
        summary[variant] = summary.get(variant, 0) + 1
    return summary


def load_candidate_tiers(
    *,
    candidate_runs: list[Path] | None,
    primary_runs: list[Path] | None,
    fallback_runs: list[Path] | None,
) -> list[dict[str, dict[str, Any]]]:
    if candidate_runs:
        return [index_rows([path]) for path in candidate_runs]
    if primary_runs and fallback_runs:
        primary = index_rows(primary_runs)
        fallback = index_rows(fallback_runs)
        return [primary, fallback]
    raise SystemExit("Provide either --candidate-run (repeatable) or both --primary-run and --fallback-run.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build an adaptive SIGIL run using verifier-gated fallback selection.")
    parser.add_argument("tasks", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--candidate-run", dest="candidate_runs", action="append", type=Path, default=None)
    parser.add_argument("--primary-run", dest="primary_runs", action="append", type=Path, default=None)
    parser.add_argument("--fallback-run", dest="fallback_runs", action="append", type=Path, default=None)
    parser.add_argument("--baseline-run", type=Path, default=None)
    parser.add_argument("--baseline-variant", default="baseline-terse")
    parser.add_argument("--variant-name", default="sigil-adaptive")
    parser.add_argument("--min-must-include", type=float, default=0.75)
    parser.add_argument("--min-exact-literal", type=float, default=0.75)
    parser.add_argument("--allow-repair", action="store_true")
    parser.add_argument("--no-require-parse", action="store_true")
    parser.add_argument("--no-require-mode-match", action="store_true")
    args = parser.parse_args(argv)

    tasks = {str(row["id"]): row for row in load_jsonl(args.tasks)}
    candidate_tiers = load_candidate_tiers(
        candidate_runs=args.candidate_runs,
        primary_runs=args.primary_runs,
        fallback_runs=args.fallback_runs,
    )
    baseline_rows: dict[str, dict[str, Any]] = {}
    if args.baseline_run is not None:
        for row in load_jsonl(args.baseline_run):
            if str(row["variant"]) != args.baseline_variant:
                continue
            baseline_rows[str(row["task_id"])] = row

    output_rows: list[dict[str, Any]] = []
    selected_primary = 0
    selected_fallback = 0
    selected_tiers: dict[str, int] = {}
    fallback_reasons: dict[str, int] = {}

    if baseline_rows:
        for task_id in tasks:
            matched = baseline_rows.get(task_id)
            if matched is None:
                raise SystemExit(f"Missing baseline row for task '{task_id}' and variant '{args.baseline_variant}'.")
            output_rows.append(matched)

    for task_id, task in tasks.items():
        task_candidates: list[dict[str, Any]] = []
        for index, tier in enumerate(candidate_tiers):
            row = tier.get(task_id)
            if row is None:
                raise SystemExit(f"Missing candidate row for task '{task_id}' in tier {index}.")
            metrics = assess_output(task, row, root=ROOT)
            failures = verification_failures(
                metrics,
                min_must_include=args.min_must_include,
                min_exact_literal=args.min_exact_literal,
                require_parse=not args.no_require_parse,
                require_mode_match=not args.no_require_mode_match,
                allow_repair=args.allow_repair,
            )
            task_candidates.append(
                {
                    "variant": row["variant"],
                    "row": row,
                    "metrics": metrics,
                    "failures": failures,
                    "tier_index": index,
                }
            )

        chosen_candidate = next((candidate for candidate in task_candidates if not candidate["failures"]), task_candidates[-1])
        chosen = dict(chosen_candidate["row"])
        selected_variant = str(chosen_candidate["variant"])
        selected_tiers[selected_variant] = selected_tiers.get(selected_variant, 0) + 1
        if chosen_candidate["tier_index"] == 0:
            selected_primary += 1
            chosen["adaptive_selected_from"] = "primary"
        else:
            selected_fallback += 1
            chosen["adaptive_selected_from"] = "fallback"
        for candidate in task_candidates:
            if candidate["tier_index"] >= chosen_candidate["tier_index"]:
                break
            for reason in candidate["failures"]:
                fallback_reasons[reason] = fallback_reasons.get(reason, 0) + 1
        rejections = [
            {"variant": candidate["variant"], "failures": candidate["failures"]}
            for candidate in task_candidates[: chosen_candidate["tier_index"]]
            if candidate["failures"]
        ]
        if rejections:
            chosen["adaptive_rejection_chain"] = rejections
            chosen["adaptive_rejection"] = rejections[0]["failures"]
        chosen["variant"] = args.variant_name
        if len(task_candidates) >= 1:
            chosen["adaptive_primary_variant"] = task_candidates[0]["variant"]
        if len(task_candidates) >= 2:
            chosen["adaptive_fallback_variant"] = task_candidates[-1]["variant"]
        chosen["adaptive_candidate_variants"] = [candidate["variant"] for candidate in task_candidates]
        chosen["adaptive_selected_variant"] = selected_variant
        chosen["adaptive_verifier"] = chosen_candidate["metrics"]
        output_rows.append(chosen)

    append_jsonl(args.out, output_rows)
    print(
        json.dumps(
            {
                "path": str(args.out),
                "count": len(output_rows),
                "selected_primary": selected_primary,
                "selected_fallback": selected_fallback,
                "selected_tiers": selected_tiers,
                "fallback_reasons": fallback_reasons,
                "variants": summarize_rows(output_rows),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
