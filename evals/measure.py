from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sigil.metrics import approx_token_count, document_metrics
from sigil.normalize import normalize_document_text, repair_direct_sigil_text
from sigil.parser import SIGILParseError, parse_document


def load_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            rows.append(json.loads(stripped))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_number}: invalid JSONL row: {exc}") from exc
    return rows


def read_content(row: dict[str, object]) -> str:
    if "content" in row:
        return str(row["content"])
    if "path" in row:
        return (ROOT / str(row["path"])).read_text(encoding="utf-8")
    raise SystemExit("Each run row must contain either 'content' or 'path'.")


def rate(hit_count: int, total: int) -> float | None:
    if total == 0:
        return None
    return hit_count / total


def summarize_variant(rows: list[dict[str, object]]) -> dict[str, object]:
    usage_rows = [row for row in rows if row["used_reported_output_tokens"]]
    input_rows = [row for row in rows if row["input_tokens"] is not None]
    uncached_input_rows = [row for row in rows if row["uncached_input_tokens"] is not None]
    total_rows = [row for row in rows if row["total_tokens"] is not None]
    effective_total_rows = [row for row in rows if row["effective_total_tokens"] is not None]
    reasoning_rows = [row for row in rows if row["reasoning_tokens"] is not None]
    cached_rows = [row for row in rows if row["cached_tokens"] is not None]
    latency_rows = [row for row in rows if row["elapsed_ms"] is not None]
    staged_rows = [row for row in rows if row["stage_count"] is not None]
    structured_target_rows = [row for row in rows if row.get("structured_expected") is True]
    structured_rows = [row for row in structured_target_rows if row["parse_ok"]]
    repaired_rows = [row for row in structured_target_rows if row["repair_parse_ok"]]
    return {
        "count": len(rows),
        "structured_expected_rate": round(mean(int(row.get("structured_expected") is True) for row in rows), 4),
        "parse_rate": round(mean(int(row["parse_ok"]) for row in structured_target_rows), 4) if structured_target_rows else None,
        "repair_parse_rate": round(mean(int(row["repair_parse_ok"]) for row in structured_target_rows), 4) if structured_target_rows else None,
        "mode_match_rate": round(mean(int(row["mode_match"]) for row in structured_target_rows), 4) if structured_target_rows else None,
        "repair_mode_match_rate": round(mean(int(row["repair_mode_match"]) for row in structured_target_rows), 4) if structured_target_rows else None,
        "must_include_rate": round(mean(row["must_include_rate"] for row in rows if row["must_include_rate"] is not None), 4)
        if any(row["must_include_rate"] is not None for row in rows)
        else None,
        "exact_literal_rate": round(mean(row["exact_literal_rate"] for row in rows if row["exact_literal_rate"] is not None), 4)
        if any(row["exact_literal_rate"] is not None for row in rows)
        else None,
        "avg_input_tokens": round(mean(row["input_tokens"] for row in input_rows), 2) if input_rows else None,
        "avg_uncached_input_tokens": round(mean(row["uncached_input_tokens"] for row in uncached_input_rows), 2) if uncached_input_rows else None,
        "avg_total_tokens": round(mean(row["total_tokens"] for row in total_rows), 2) if total_rows else None,
        "avg_effective_total_tokens": round(mean(row["effective_total_tokens"] for row in effective_total_rows), 2) if effective_total_rows else None,
        "avg_cached_tokens": round(mean(row["cached_tokens"] for row in cached_rows), 2) if cached_rows else None,
        "avg_output_tokens": round(mean(row["output_tokens"] for row in rows), 2),
        "avg_reasoning_tokens": round(mean(row["reasoning_tokens"] for row in reasoning_rows), 2) if reasoning_rows else None,
        "avg_elapsed_ms": round(mean(row["elapsed_ms"] for row in latency_rows), 2) if latency_rows else None,
        "avg_stage_count": round(mean(row["stage_count"] for row in staged_rows), 2) if staged_rows else None,
        "avg_clause_count": round(mean(row["clause_count"] for row in structured_rows), 2) if structured_rows else None,
        "avg_repair_clause_count": round(mean(row["repair_clause_count"] for row in repaired_rows), 2) if repaired_rows else None,
        "avg_codebook_size": round(mean(row["codebook_size"] for row in structured_rows), 2) if structured_rows else None,
        "audit_rate": round(mean(int(row["has_audit"]) for row in structured_rows), 4) if structured_rows else None,
        "token_source_usage_rate": round(len(usage_rows) / len(rows), 4),
    }


def compare_to_baseline(rows: list[dict[str, object]], baseline_rows: list[dict[str, object]]) -> dict[str, object] | None:
    baseline_by_task = {row["task_id"]: row for row in baseline_rows}
    ratios: list[float] = []
    total_ratios: list[float] = []
    effective_total_ratios: list[float] = []
    latency_ratios: list[float] = []
    output_values: list[tuple[float, float]] = []
    total_values: list[tuple[float, float]] = []
    effective_total_values: list[tuple[float, float]] = []
    latency_values: list[tuple[float, float]] = []
    for row in rows:
        baseline = baseline_by_task.get(row["task_id"])
        if not baseline:
            continue
        if baseline["output_tokens"] == 0:
            continue
        ratios.append(row["output_tokens"] / baseline["output_tokens"])
        output_values.append((float(row["output_tokens"]), float(baseline["output_tokens"])))
        if row["total_tokens"] is not None and baseline["total_tokens"] not in {None, 0}:
            total_ratios.append(row["total_tokens"] / baseline["total_tokens"])
            total_values.append((float(row["total_tokens"]), float(baseline["total_tokens"])))
        if row["effective_total_tokens"] is not None and baseline["effective_total_tokens"] not in {None, 0}:
            effective_total_ratios.append(row["effective_total_tokens"] / baseline["effective_total_tokens"])
            effective_total_values.append((float(row["effective_total_tokens"]), float(baseline["effective_total_tokens"])))
        if row["elapsed_ms"] is not None and baseline["elapsed_ms"] not in {None, 0}:
            latency_ratios.append(row["elapsed_ms"] / baseline["elapsed_ms"])
            latency_values.append((float(row["elapsed_ms"]), float(baseline["elapsed_ms"])))
    if not ratios:
        return None
    summary = {
        "avg_token_ratio_vs_baseline": round(mean(ratios), 4),
        "avg_token_savings_vs_baseline": round(1 - mean(ratios), 4),
        "paired_tasks": len(ratios),
    }
    if output_values:
        summary["aggregate_token_ratio_vs_baseline"] = round(
            sum(current for current, _ in output_values) / sum(reference for _, reference in output_values), 4
        )
        summary["aggregate_token_savings_vs_baseline"] = round(1 - summary["aggregate_token_ratio_vs_baseline"], 4)
    if total_ratios:
        summary["avg_total_token_ratio_vs_baseline"] = round(mean(total_ratios), 4)
        summary["avg_total_token_savings_vs_baseline"] = round(1 - mean(total_ratios), 4)
    if total_values:
        summary["aggregate_total_token_ratio_vs_baseline"] = round(
            sum(current for current, _ in total_values) / sum(reference for _, reference in total_values), 4
        )
        summary["aggregate_total_token_savings_vs_baseline"] = round(
            1 - summary["aggregate_total_token_ratio_vs_baseline"], 4
        )
    if effective_total_ratios:
        summary["avg_effective_total_ratio_vs_baseline"] = round(mean(effective_total_ratios), 4)
        summary["avg_effective_total_savings_vs_baseline"] = round(1 - mean(effective_total_ratios), 4)
    if effective_total_values:
        summary["aggregate_effective_total_ratio_vs_baseline"] = round(
            sum(current for current, _ in effective_total_values) / sum(reference for _, reference in effective_total_values),
            4,
        )
        summary["aggregate_effective_total_savings_vs_baseline"] = round(
            1 - summary["aggregate_effective_total_ratio_vs_baseline"], 4
        )
    if latency_ratios:
        summary["avg_latency_ratio_vs_baseline"] = round(mean(latency_ratios), 4)
        summary["avg_latency_savings_vs_baseline"] = round(1 - mean(latency_ratios), 4)
    if latency_values:
        summary["aggregate_latency_ratio_vs_baseline"] = round(
            sum(current for current, _ in latency_values) / sum(reference for _, reference in latency_values), 4
        )
        summary["aggregate_latency_savings_vs_baseline"] = round(1 - summary["aggregate_latency_ratio_vs_baseline"], 4)
    return summary


def measure_run(tasks_path: Path, run_path: Path, baseline: str | None = None) -> dict[str, object]:
    tasks = {row["id"]: row for row in load_jsonl(tasks_path)}
    run_rows = load_jsonl(run_path)
    results: list[dict[str, object]] = []

    for row in run_rows:
        task_id = str(row["task_id"])
        if task_id not in tasks:
            raise SystemExit(f"Unknown task_id in run file: {task_id}")
        task = tasks[task_id]
        content = read_content(row)
        usage = row.get("usage") or {}
        output_tokens = usage.get("output_tokens")
        reasoning_tokens = usage.get("reasoning_tokens")
        cached_tokens = usage.get("cached_tokens")
        if output_tokens is None:
            output_tokens = approx_token_count(content)
        input_tokens = usage.get("input_tokens")
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

        result = {
            "task_id": task_id,
            "variant": str(row["variant"]),
            "model": row.get("model"),
            "input_tokens": input_tokens,
            "uncached_input_tokens": uncached_input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": usage.get("total_tokens"),
            "effective_total_tokens": effective_total_tokens,
            "reasoning_tokens": reasoning_tokens,
            "cached_tokens": cached_tokens,
            "elapsed_ms": row.get("elapsed_ms"),
            "stage_count": usage.get("stage_count", 1 if usage else None),
            "used_reported_output_tokens": usage.get("output_tokens") is not None,
            "structured_expected": row.get("structured_expected"),
            "must_include_rate": rate(must_include_hits, len(must_include)),
            "exact_literal_rate": rate(exact_literal_hits, len(exact_literals)),
            "parse_ok": False,
            "parse_error": None,
            "mode_match": False,
            "clause_count": None,
            "codebook_size": None,
            "has_audit": None,
            "repair_parse_ok": False,
            "repair_parse_error": None,
            "repair_mode_match": False,
            "repair_clause_count": None,
        }

        try:
            document = parse_document(content)
        except SIGILParseError as exc:
            result["parse_error"] = str(exc)
        else:
            stats = document_metrics(document, content)
            result["parse_ok"] = True
            result["mode_match"] = stats["mode"] == task.get("mode")
            result["clause_count"] = stats["clause_count"]
            result["codebook_size"] = stats["codebook_size"]
            result["has_audit"] = stats["has_audit"]

        if row.get("transport") == "sigil":
            repaired_content = repair_direct_sigil_text(content, str(task.get("category") or ""))
        else:
            repaired_content = normalize_document_text(content)
        try:
            repaired_document = parse_document(repaired_content)
        except SIGILParseError as exc:
            result["repair_parse_error"] = str(exc)
        else:
            repaired_stats = document_metrics(repaired_document, repaired_content)
            result["repair_parse_ok"] = True
            result["repair_mode_match"] = repaired_stats["mode"] == task.get("mode")
            result["repair_clause_count"] = repaired_stats["clause_count"]

        results.append(result)

    by_variant: dict[str, list[dict[str, object]]] = defaultdict(list)
    for result in results:
        by_variant[str(result["variant"])].append(result)

    summary: dict[str, object] = {
        "tasks": str(tasks_path),
        "run": str(run_path),
        "variants": {},
    }

    for variant, rows in sorted(by_variant.items()):
        variant_summary = summarize_variant(rows)
        if baseline and variant != baseline and baseline in by_variant:
            variant_summary["baseline_comparison"] = compare_to_baseline(rows, by_variant[baseline])
        summary["variants"][variant] = variant_summary

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure SIGIL evaluation runs.")
    parser.add_argument("tasks", type=Path)
    parser.add_argument("run", type=Path)
    parser.add_argument("--baseline", default=None, help="Variant name to use as compression baseline.")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary.")
    args = parser.parse_args(argv)

    summary = measure_run(args.tasks, args.run, args.baseline)

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(summary, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
