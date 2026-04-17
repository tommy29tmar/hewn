from __future__ import annotations

import importlib.util
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from contextlib import redirect_stdout

from .eval_common import load_jsonl
from .metrics import approx_token_count
from .normalize import normalize_document_text, repair_direct_flint_text
from .parser import FlintParseError, parse_document
from .contracts import infer_contract_family

ROOT = Path(__file__).resolve().parents[2]
_MODULE_CACHE: dict[str, object] = {}

METRIC_MAP = {
    "total": {
        "summary_key": "avg_total_tokens",
        "savings_key": "aggregate_total_token_savings_vs_baseline",
        "label": "total tokens",
    },
    "effective_total": {
        "summary_key": "avg_effective_total_tokens",
        "savings_key": "aggregate_effective_total_savings_vs_baseline",
        "label": "effective total tokens",
    },
    "output": {
        "summary_key": "avg_output_tokens",
        "savings_key": "aggregate_token_savings_vs_baseline",
        "label": "output tokens",
    },
}


def _load_repo_module(name: str, relative_path: str) -> object:
    cached = _MODULE_CACHE.get(name)
    if cached is not None:
        return cached
    module_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    _MODULE_CACHE[name] = module
    return module


def _repo_path(path: str | Path) -> Path:
    raw = Path(path)
    if raw.is_absolute():
        return raw
    return ROOT / raw


def _normalize_provider(provider: str | None, model: str | None) -> str:
    normalized = (provider or "").strip().lower()
    if normalized and normalized != "unknown":
        return normalized
    model_name = (model or "").strip().lower()
    if model_name.startswith(("gpt-", "o1", "o3", "o4")):
        return "openai"
    if "claude" in model_name:
        return "anthropic"
    if "gemini" in model_name:
        return "gemini"
    return normalized or "unknown"


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _fmt_number(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.2f}"
    return str(value)


def _fmt_percent(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.2f}%"


def corpus_summary(path: Path) -> dict[str, object]:
    rows = load_jsonl(path)
    category_counts: dict[str, int] = {}
    prompt_tokens: list[int] = []
    for row in rows:
        category = str(row.get("category") or "uncategorized")
        category_counts[category] = category_counts.get(category, 0) + 1
        prompt = row.get("prompt")
        if prompt is not None:
            prompt_tokens.append(approx_token_count(str(prompt)))
    return {
        "path": str(path),
        "count": len(rows),
        "categories": category_counts,
        "avg_prompt_tokens": round(sum(prompt_tokens) / len(prompt_tokens), 2) if prompt_tokens else None,
    }


def build_extended_corpus(out_dir: Path) -> dict[str, object]:
    module = _load_repo_module("sigil_eval_build_extended_corpus", "evals/build_extended_corpus.py")
    exit_code = module.main(["--out-dir", str(out_dir)])
    if exit_code != 0:
        raise SystemExit(exit_code)
    outputs = {
        "hybrid": out_dir / "tasks_hybrid_micro_extended.jsonl",
        "debugging": out_dir / "tasks_debug_micro_extended.jsonl",
        "architecture": out_dir / "tasks_architecture_micro_extended.jsonl",
        "code_review": out_dir / "tasks_review_micro_extended.jsonl",
        "refactoring": out_dir / "tasks_refactor_micro_extended.jsonl",
    }
    return {
        "outputs": {name: str(path) for name, path in outputs.items()},
        "summary": {name: corpus_summary(path) for name, path in outputs.items()},
    }


def build_macro_tasks(source: Path, prefix: Path, out: Path, task_label: str = "Task") -> dict[str, object]:
    module = _load_repo_module("sigil_eval_build_macro_tasks", "evals/build_macro_tasks.py")
    exit_code = module.main([str(source), str(prefix), str(out), "--task-label", task_label])
    if exit_code != 0:
        raise SystemExit(exit_code)
    return corpus_summary(out)


def build_compiled_macro_tasks(
    source: Path,
    prefix: Path,
    out: Path,
    *,
    context_style: str = "cacheable",
    task_label: str = "Task",
) -> dict[str, object]:
    module = _load_repo_module("sigil_eval_build_compiled_macro_tasks", "evals/build_compiled_macro_tasks.py")
    exit_code = module.main(
        [
            str(source),
            str(prefix),
            str(out),
            "--context-style",
            context_style,
            "--task-label",
            task_label,
        ]
    )
    if exit_code != 0:
        raise SystemExit(exit_code)
    return corpus_summary(out)


def build_task_capsules(source: Path, out: Path, style: str = "v1") -> dict[str, object]:
    module = _load_repo_module("sigil_eval_build_task_capsules", "evals/build_task_capsules.py")
    exit_code = module.main([str(source), str(out), "--style", style])
    if exit_code != 0:
        raise SystemExit(exit_code)
    return corpus_summary(out)


def build_adaptive_run(
    tasks: Path,
    out: Path,
    *,
    candidate_runs: list[Path] | None = None,
    primary_runs: list[Path],
    fallback_runs: list[Path],
    baseline_run: Path | None = None,
    baseline_variant: str = "baseline-terse",
    variant_name: str = "sigil-adaptive",
    min_must_include: float = 0.75,
    min_exact_literal: float = 0.75,
    allow_repair: bool = False,
    require_parse: bool = True,
    require_mode_match: bool = True,
) -> dict[str, object]:
    module = _load_repo_module("sigil_eval_build_adaptive_run", "evals/build_adaptive_run.py")
    command = [str(tasks), str(out)]
    if candidate_runs:
        for path in candidate_runs:
            command.extend(["--candidate-run", str(path)])
    else:
        for path in primary_runs:
            command.extend(["--primary-run", str(path)])
        for path in fallback_runs:
            command.extend(["--fallback-run", str(path)])
    if baseline_run is not None:
        command.extend(["--baseline-run", str(baseline_run), "--baseline-variant", baseline_variant])
    command.extend(
        [
            "--variant-name",
            variant_name,
            "--min-must-include",
            str(min_must_include),
            "--min-exact-literal",
            str(min_exact_literal),
        ]
    )
    if allow_repair:
        command.append("--allow-repair")
    if not require_parse:
        command.append("--no-require-parse")
    if not require_mode_match:
        command.append("--no-require-mode-match")
    with redirect_stdout(io.StringIO()):
        exit_code = module.main(command)
    if exit_code != 0:
        raise SystemExit(exit_code)
    rows = load_jsonl(out)
    variant_counts: dict[str, int] = {}
    selected_primary = 0
    selected_fallback = 0
    for row in rows:
        variant = str(row["variant"])
        variant_counts[variant] = variant_counts.get(variant, 0) + 1
        if row.get("adaptive_selected_from") == "primary":
            selected_primary += 1
        elif row.get("adaptive_selected_from") == "fallback":
            selected_fallback += 1
    return {
        "path": str(out),
        "count": len(rows),
        "variants": variant_counts,
        "selected_primary": selected_primary,
        "selected_fallback": selected_fallback,
    }


def _metric_config(metric_name: str) -> dict[str, str]:
    if metric_name not in METRIC_MAP:
        known = ", ".join(sorted(METRIC_MAP))
        raise SystemExit(f"Unknown primary_metric '{metric_name}'. Expected one of: {known}")
    return METRIC_MAP[metric_name]


def _summarize_entry(entry: dict[str, object]) -> dict[str, object]:
    measure_module = _load_repo_module("sigil_eval_measure", "evals/measure.py")
    cache_module = _load_repo_module("sigil_eval_cache_report", "evals/cache_report.py")

    tasks_path = _repo_path(str(entry["tasks"]))
    run_path = _repo_path(str(entry["run"]))
    baseline_variant = str(entry.get("baseline") or "baseline-terse")
    sigil_variant = str(entry.get("variant") or "sigil-routed")
    metric_name = str(entry.get("primary_metric") or "total")
    metric_cfg = _metric_config(metric_name)

    summary = measure_module.measure_run(tasks_path, run_path, baseline_variant)
    variants = summary["variants"]
    if baseline_variant not in variants:
        raise SystemExit(f"Baseline variant '{baseline_variant}' not found in {run_path}")
    if sigil_variant not in variants:
        raise SystemExit(f"Variant '{sigil_variant}' not found in {run_path}")

    baseline = variants[baseline_variant]
    sigil = variants[sigil_variant]
    comparison = sigil.get("baseline_comparison") or {}
    metric_savings = comparison.get(metric_cfg["savings_key"])
    if metric_savings is None:
        fallback_key = metric_cfg["savings_key"].replace("aggregate_", "avg_")
        metric_savings = comparison.get(fallback_key)

    cache_verdict = None
    cache_rate = None
    if entry.get("provider") and entry.get("model"):
        cache_summary = cache_module.summarize_run(run_path, str(entry["provider"]), str(entry["model"]))
        variant_cache = cache_summary["variants"].get(sigil_variant)
        if variant_cache is not None:
            cache_verdict = variant_cache.get("verdict")
            cache_rate = variant_cache.get("cache_hit_rate")

    return {
        "label": entry.get("label"),
        "provider": entry.get("provider"),
        "model": entry.get("model"),
        "regime": entry.get("regime"),
        "router": entry.get("router"),
        "baseline_variant": baseline_variant,
        "variant": sigil_variant,
        "metric_name": metric_name,
        "metric_label": metric_cfg["label"],
        "sigil_metric": sigil.get(metric_cfg["summary_key"]),
        "baseline_metric": baseline.get(metric_cfg["summary_key"]),
        "metric_savings": metric_savings,
        "parse_rate": sigil.get("parse_rate"),
        "must_include_rate": sigil.get("must_include_rate"),
        "exact_literal_rate": sigil.get("exact_literal_rate"),
        "latency_savings": (sigil.get("baseline_comparison") or {}).get("avg_latency_savings_vs_baseline"),
        "cache_verdict": cache_verdict,
        "cache_hit_rate": cache_rate,
        "notes": entry.get("notes"),
        "tasks": _display_path(tasks_path),
        "run": _display_path(run_path),
    }


def render_report(manifest_path: Path, out_path: Path | None = None) -> str:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    title = str(manifest.get("title") or "SIGIL Benchmark Matrix")
    thesis = [str(item) for item in manifest.get("thesis", [])]
    entries = [_summarize_entry(entry) for entry in manifest.get("entries", [])]
    corpora = [
        {"label": str(item["label"]), **corpus_summary(_repo_path(str(item["path"])))}
        for item in manifest.get("corpora", [])
    ]

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# {title}",
        "",
        f"_Generated by `sigil bench report` on {generated_at}._",
        "",
    ]

    if thesis:
        lines.append("## Thesis")
        lines.append("")
        for item in thesis:
            lines.append(f"- {item}")
        lines.append("")

    if entries:
        lines.extend(
            [
                "## Provider Matrix",
                "",
                "| Provider | Model | Regime | Router | Primary metric | SIGIL | Baseline | Savings | Parse | Must | Literal | Latency | Cache |",
                "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for item in entries:
            lines.append(
                "| {provider} | {model} | {regime} | {router} | {metric_label} | {sigil_metric} | {baseline_metric} | {metric_savings} | {parse_rate} | {must_include_rate} | {exact_literal_rate} | {latency_savings} | {cache} |".format(
                    provider=item.get("provider") or "n/a",
                    model=item.get("model") or "n/a",
                    regime=item.get("regime") or "n/a",
                    router=item.get("router") or "n/a",
                    metric_label=item["metric_label"],
                    sigil_metric=_fmt_number(item["sigil_metric"]),
                    baseline_metric=_fmt_number(item["baseline_metric"]),
                    metric_savings=_fmt_percent(item["metric_savings"]),
                    parse_rate=_fmt_percent(item["parse_rate"]),
                    must_include_rate=_fmt_percent(item["must_include_rate"]),
                    exact_literal_rate=_fmt_percent(item["exact_literal_rate"]),
                    latency_savings=_fmt_percent(item["latency_savings"]),
                    cache=item["cache_verdict"] or "n/a",
                )
            )
        lines.append("")

        lines.append("## Notes")
        lines.append("")
        for item in entries:
            note = item.get("notes")
            if not note:
                continue
            lines.append(
                "- **{label}**: {note} Source: `{tasks}` / `{run}`.".format(
                    label=item.get("label") or item.get("model") or "run",
                    note=note,
                    tasks=item["tasks"],
                    run=item["run"],
                )
            )
        lines.append("")

    if corpora:
        lines.extend(
            [
                "## Corpus Inventory",
                "",
                "| Corpus | Tasks | Categories | Avg prompt tokens |",
                "| --- | ---: | --- | ---: |",
            ]
        )
        for corpus in corpora:
            categories = ", ".join(f"{name}:{count}" for name, count in sorted(corpus["categories"].items()))
            lines.append(
                "| {label} | {count} | {categories} | {avg_prompt_tokens} |".format(
                    label=corpus["label"],
                    count=corpus["count"],
                    categories=categories,
                    avg_prompt_tokens=_fmt_number(corpus["avg_prompt_tokens"]),
                )
            )
        lines.append("")

    markdown = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown, encoding="utf-8")
    return markdown


def render_portability_report(tasks_path: Path, run_paths: list[Path], out_path: Path | None = None) -> str:
    tasks = {str(row["id"]): row for row in load_jsonl(tasks_path)}
    grouped: dict[tuple[str, str, str, str], list[dict[str, object]]] = {}
    baselines: dict[tuple[str, str, str], dict[str, object]] = {}

    for run_path in run_paths:
        for row in load_jsonl(run_path):
            task_id = str(row["task_id"])
            task = tasks[task_id]
            model = str(row.get("model") or "unknown")
            provider = _normalize_provider(str(row.get("provider") or "unknown"), model)
            variant = str(row.get("variant") or "unknown")
            category = str(task.get("category") or "uncategorized")
            family = infer_contract_family(str(row.get("prompt_path") or ""), variant)
            usage = row.get("usage") or {}
            content = str(row.get("content") or "")
            output_tokens = float(usage.get("output_tokens") or approx_token_count(content))
            input_tokens = usage.get("input_tokens")
            total_tokens = usage.get("total_tokens")
            effective_total_tokens = (
                float(max(0, input_tokens - (usage.get("cached_tokens") or 0)) + output_tokens)
                if input_tokens is not None
                else float(total_tokens or output_tokens)
            )
            must_include = [str(item) for item in task.get("must_include", [])]
            exact_literals = [str(item) for item in task.get("exact_literals", [])]
            lowered = content.lower()
            must_include_rate = (
                sum(1 for item in must_include if item.lower() in lowered) / len(must_include) if must_include else 0.0
            )
            exact_literal_rate = sum(1 for item in exact_literals if item in content) / len(exact_literals) if exact_literals else 0.0
            parse_ok = None
            if row.get("structured_expected") is True:
                repaired = (
                    repair_direct_flint_text(content, str(task.get("category") or ""))
                    if row.get("transport") == "sigil"
                    else normalize_document_text(content)
                )
                try:
                    parse_document(repaired)
                except FlintParseError:
                    parse_ok = 0.0
                else:
                    parse_ok = 1.0
            record = {
                "task_id": task_id,
                "provider": provider,
                "model": model,
                "variant": variant,
                "category": category,
                "family": family.name,
                "origin_provider": family.origin_provider,
                "output_tokens": output_tokens,
                "effective_total_tokens": effective_total_tokens,
                "elapsed_ms": float(row.get("elapsed_ms") or 0.0),
                "must_include_rate": must_include_rate,
                "exact_literal_rate": exact_literal_rate,
                "parse_rate": parse_ok,
            }
            if family.name == "baseline":
                baselines[(provider, model, task_id)] = record
            grouped.setdefault((provider, model, category, family.name), []).append(record)

    entries: list[dict[str, object]] = []
    for (provider, model, category, family_name), rows in sorted(grouped.items()):
        origin = rows[0]["origin_provider"]
        parse_rows = [float(row["parse_rate"]) for row in rows if row["parse_rate"] is not None]
        current_pairs = []
        latency_pairs = []
        for row in rows:
            baseline = baselines.get((provider, model, str(row["task_id"])))
            if baseline is None or family_name == "baseline":
                continue
            current_pairs.append((float(row["effective_total_tokens"]), float(baseline["effective_total_tokens"])))
            latency_pairs.append((float(row["elapsed_ms"]), float(baseline["elapsed_ms"])))
        aggregate_savings = None
        latency_savings = None
        if current_pairs:
            aggregate_savings = 1 - (sum(cur for cur, _ in current_pairs) / sum(base for _, base in current_pairs))
        if latency_pairs:
            latency_savings = 1 - (sum(cur for cur, _ in latency_pairs) / sum(base for _, base in latency_pairs))
        entries.append(
            {
                "provider": provider,
                "model": model,
                "category": category,
                "family": family_name,
                "origin_provider": origin,
                "count": len(rows),
                "parse_rate": round(mean(parse_rows), 4) if parse_rows else None,
                "must_include_rate": round(mean(float(row["must_include_rate"]) for row in rows), 4),
                "exact_literal_rate": round(mean(float(row["exact_literal_rate"]) for row in rows), 4),
                "avg_effective_total_tokens": round(mean(float(row["effective_total_tokens"]) for row in rows), 2),
                "avg_output_tokens": round(mean(float(row["output_tokens"]) for row in rows), 2),
                "avg_elapsed_ms": round(mean(float(row["elapsed_ms"]) for row in rows), 2),
                "aggregate_effective_total_savings_vs_baseline": round(aggregate_savings, 4) if aggregate_savings is not None else None,
                "aggregate_latency_savings_vs_baseline": round(latency_savings, 4) if latency_savings is not None else None,
            }
        )

    lines = [
        "# SIGIL Contract Portability",
        "",
        f"_Generated by `sigil bench portability-report` on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}._",
        "",
        "| Provider | Model | Category | Family | Origin | Avg effective total | Savings vs baseline | Parse | Must | Literal | Latency |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for entry in entries:
        lines.append(
            "| {provider} | {model} | {category} | {family} | {origin_provider} | {avg_effective_total_tokens} | {savings} | {parse} | {must} | {literal} | {latency} |".format(
                provider=entry["provider"],
                model=entry["model"],
                category=entry["category"],
                family=entry["family"],
                origin_provider=entry["origin_provider"],
                avg_effective_total_tokens=_fmt_number(entry["avg_effective_total_tokens"]),
                savings=_fmt_percent(entry["aggregate_effective_total_savings_vs_baseline"]),
                parse=_fmt_percent(entry["parse_rate"]),
                must=_fmt_percent(entry["must_include_rate"]),
                literal=_fmt_percent(entry["exact_literal_rate"]),
                latency=_fmt_percent(entry["aggregate_latency_savings_vs_baseline"]),
            )
        )
    lines.append("")
    markdown = "\n".join(lines)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown, encoding="utf-8")
    return markdown
