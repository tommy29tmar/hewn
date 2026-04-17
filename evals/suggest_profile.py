from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flint.metrics import approx_token_count, document_metrics
from flint.normalize import normalize_document_text, repair_direct_flint_text
from flint.parser import FlintParseError, parse_document


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


def read_content(row: dict[str, Any]) -> str:
    if "content" in row:
        return str(row["content"])
    if "path" in row:
        return (ROOT / str(row["path"])).read_text(encoding="utf-8")
    raise SystemExit("Each run row must contain either 'content' or 'path'.")


def rate(hit_count: int, total: int) -> float | None:
    if total == 0:
        return None
    return hit_count / total


def evaluate_rows(tasks_path: Path, run_paths: list[Path]) -> list[dict[str, Any]]:
    tasks = {str(row["id"]): row for row in load_jsonl(tasks_path)}
    results: list[dict[str, Any]] = []
    for run_path in run_paths:
        for row in load_jsonl(run_path):
            task_id = str(row["task_id"])
            task = tasks[task_id]
            content = read_content(row)
            usage = row.get("usage") or {}
            output_tokens = usage.get("output_tokens")
            if output_tokens is None:
                output_tokens = approx_token_count(content)
            input_tokens = usage.get("input_tokens")
            cached_tokens = usage.get("cached_tokens")
            uncached_input_tokens = None
            effective_total_tokens = None
            if input_tokens is not None:
                uncached_input_tokens = max(0, input_tokens - (cached_tokens or 0))
                effective_total_tokens = uncached_input_tokens + output_tokens

            must_include = [str(item) for item in task.get("must_include", [])]
            exact_literals = [str(item) for item in task.get("exact_literals", [])]
            lowered = content.lower()
            must_include_hits = sum(1 for item in must_include if item.lower() in lowered)
            exact_literal_hits = sum(1 for item in exact_literals if item in content)

            parse_ok = False
            mode_match = False
            repaired_parse_ok = False
            repaired_mode_match = False
            try:
                document = parse_document(content)
            except FlintParseError:
                pass
            else:
                stats = document_metrics(document, content)
                parse_ok = True
                mode_match = stats["mode"] == task.get("mode")

            if row.get("transport") == "sigil":
                repaired_content = repair_direct_flint_text(content, str(task.get("category") or ""))
            else:
                repaired_content = normalize_document_text(content)
            try:
                repaired_document = parse_document(repaired_content)
            except FlintParseError:
                pass
            else:
                repaired_stats = document_metrics(repaired_document, repaired_content)
                repaired_parse_ok = True
                repaired_mode_match = repaired_stats["mode"] == task.get("mode")

            results.append(
                {
                    "task_id": task_id,
                    "category": str(task["category"]),
                    "variant": str(row["variant"]),
                    "structured_expected": bool(row.get("structured_expected") is True),
                    "parse_rate": 1.0 if parse_ok else 0.0,
                    "repair_parse_rate": 1.0 if repaired_parse_ok else 0.0,
                    "mode_match_rate": 1.0 if mode_match else 0.0,
                    "repair_mode_match_rate": 1.0 if repaired_mode_match else 0.0,
                    "must_include_rate": rate(must_include_hits, len(must_include)) or 0.0,
                    "exact_literal_rate": rate(exact_literal_hits, len(exact_literals)) or 0.0,
                    "output_tokens": float(output_tokens),
                    "effective_total_tokens": float(effective_total_tokens) if effective_total_tokens is not None else float(usage.get("total_tokens") or output_tokens),
                    "elapsed_ms": float(row.get("elapsed_ms") or 0.0),
                }
            )
    return results


def aggregate_by_category(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, float]]]:
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row["category"]][row["variant"]].append(row)

    summary: dict[str, dict[str, dict[str, float]]] = {}
    for category, variants in grouped.items():
        summary[category] = {}
        for variant, variant_rows in variants.items():
            summary[category][variant] = {
                key: mean(float(r[key]) for r in variant_rows)
                for key in (
                    "parse_rate",
                    "repair_parse_rate",
                    "mode_match_rate",
                    "repair_mode_match_rate",
                    "must_include_rate",
                    "exact_literal_rate",
                    "output_tokens",
                    "effective_total_tokens",
                    "elapsed_ms",
                )
            }
            summary[category][variant]["structured_expected_rate"] = mean(
                float(r["structured_expected"]) for r in variant_rows
            )
    return summary


def aggregate_by_task(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, float]]]:
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row["task_id"]][row["variant"]].append(row)

    summary: dict[str, dict[str, dict[str, float]]] = {}
    for task_id, variants in grouped.items():
        summary[task_id] = {}
        for variant, variant_rows in variants.items():
            summary[task_id][variant] = {
                key: mean(float(r[key]) for r in variant_rows)
                for key in (
                    "parse_rate",
                    "repair_parse_rate",
                    "mode_match_rate",
                    "repair_mode_match_rate",
                    "must_include_rate",
                    "exact_literal_rate",
                    "output_tokens",
                    "effective_total_tokens",
                    "elapsed_ms",
                )
            }
            summary[task_id][variant]["structured_expected_rate"] = mean(
                float(r["structured_expected"]) for r in variant_rows
            )
    return summary


def score_variant(metric: dict[str, float], objective: str, ranges: dict[str, tuple[float, float]]) -> float:
    def norm_high(name: str) -> float:
        low, high = ranges[name]
        value = metric[name]
        if high == low:
            return 1.0
        return (value - low) / (high - low)

    def norm_low(name: str) -> float:
        low, high = ranges[name]
        value = metric[name]
        if high == low:
            return 1.0
        return 1.0 - ((value - low) / (high - low))

    parse_guard = min(metric["parse_rate"], metric["repair_parse_rate"], metric["mode_match_rate"], metric["repair_mode_match_rate"])
    if objective == "quality":
        return (
            5.0 * parse_guard
            + 2.5 * norm_high("must_include_rate")
            + 2.0 * norm_high("exact_literal_rate")
            + 0.5 * norm_low("effective_total_tokens")
            + 0.25 * norm_low("elapsed_ms")
        )
    if objective == "balanced":
        return (
            4.5 * parse_guard
            + 1.75 * norm_high("must_include_rate")
            + 1.5 * norm_high("exact_literal_rate")
            + 1.75 * norm_low("effective_total_tokens")
            + 1.0 * norm_low("output_tokens")
            + 0.5 * norm_low("elapsed_ms")
        )
    return (
        4.0 * parse_guard
        + 2.0 * norm_low("effective_total_tokens")
        + 1.5 * norm_low("output_tokens")
        + 1.0 * norm_low("elapsed_ms")
        + 1.0 * norm_high("must_include_rate")
        + 0.5 * norm_high("exact_literal_rate")
    )


def parse_guard(metric: dict[str, float], allow_plain_candidates: bool = False) -> float:
    if allow_plain_candidates and metric.get("structured_expected_rate", 1.0) == 0.0:
        return 1.0
    return min(metric["parse_rate"], metric["repair_parse_rate"], metric["mode_match_rate"], metric["repair_mode_match_rate"])


def build_efficiency_key(
    metric: dict[str, float],
    best_metric: dict[str, float],
    *,
    allow_plain_candidates: bool = False,
) -> tuple[float, ...]:
    must_floor = max(0.5, best_metric["must_include_rate"] - 0.5)
    literal_floor = max(0.5, best_metric["exact_literal_rate"] - 0.5)
    eligible = (
        parse_guard(metric, allow_plain_candidates=allow_plain_candidates) >= 1.0
        and metric["must_include_rate"] >= must_floor
        and metric["exact_literal_rate"] >= literal_floor
    )
    return (
        0.0 if eligible else 1.0,
        metric["effective_total_tokens"],
        metric["elapsed_ms"],
        metric["output_tokens"],
        -metric["must_include_rate"],
        -metric["exact_literal_rate"],
    )


def build_profile(
    summary: dict[str, dict[str, dict[str, float]]],
    objective: str,
    profile_name: str,
    *,
    allow_plain_candidates: bool = False,
    granularity: str = "category",
) -> dict[str, Any]:
    categories: dict[str, str] = {}
    tasks: dict[str, str] = {}
    diagnostics: dict[str, Any] = {}
    target_map = categories if granularity == "category" else tasks
    for key_name, variants in summary.items():
        ranges: dict[str, tuple[float, float]] = {}
        for metric_name in (
            "must_include_rate",
            "exact_literal_rate",
            "output_tokens",
            "effective_total_tokens",
            "elapsed_ms",
        ):
            values = [metric[metric_name] for metric in variants.values()]
            ranges[metric_name] = (min(values), max(values))
        scored: list[tuple[float, str]] = []
        diagnostics[key_name] = {}
        best_metric = {
            "must_include_rate": max(metric["must_include_rate"] for metric in variants.values()),
            "exact_literal_rate": max(metric["exact_literal_rate"] for metric in variants.values()),
        }
        for variant, metric in variants.items():
            score = score_variant(metric, objective=objective, ranges=ranges)
            diagnostic = {"score": round(score, 4), **{k: round(v, 4) for k, v in metric.items()}}
            if objective == "efficiency":
                key = build_efficiency_key(
                    metric,
                    best_metric,
                    allow_plain_candidates=allow_plain_candidates,
                )
                diagnostic["efficiency_eligible"] = key[0] == 0.0
                diagnostic["efficiency_key"] = [round(value, 4) for value in key]
            diagnostics[key_name][variant] = diagnostic
            scored.append((score, variant))
        if objective == "efficiency":
            target_map[key_name] = min(
                variants.items(),
                key=lambda item: build_efficiency_key(
                    item[1],
                    best_metric,
                    allow_plain_candidates=allow_plain_candidates,
                ),
            )[0]
        else:
            scored.sort(reverse=True)
            target_map[key_name] = scored[0][1]
    profile = {
        "name": profile_name,
        "objective": objective,
        "granularity": granularity,
        "allow_plain_candidates": allow_plain_candidates,
        "diagnostics": diagnostics,
    }
    if categories:
        profile["categories"] = categories
    if tasks:
        profile["tasks"] = tasks
    return profile


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Suggest a SIGIL routing profile from benchmark runs.")
    parser.add_argument("tasks", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--name", default=None, help="Optional profile name. Defaults to the output filename stem.")
    parser.add_argument("--objective", choices=["quality", "efficiency", "balanced"], default="efficiency")
    parser.add_argument("--granularity", choices=["category", "task"], default="category")
    parser.add_argument("--run", dest="runs", action="append", type=Path, required=True, help="Run JSONL to include. Repeatable.")
    parser.add_argument("--allow-plain-candidates", action="store_true", help="Let non-SIGIL baseline variants compete in profile selection.")
    args = parser.parse_args(argv)

    rows = evaluate_rows(args.tasks, args.runs)
    summary = aggregate_by_category(rows) if args.granularity == "category" else aggregate_by_task(rows)
    profile_name = args.name or args.out.stem
    profile = build_profile(
        summary,
        objective=args.objective,
        profile_name=profile_name,
        allow_plain_candidates=args.allow_plain_candidates,
        granularity=args.granularity,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(profile, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
