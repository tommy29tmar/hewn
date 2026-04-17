from __future__ import annotations

from pathlib import Path
from typing import Any

from .metrics import approx_token_count, document_metrics
from .normalize import normalize_document_text, repair_direct_flint_text
from .parser import FlintParseError, parse_document


def rate(hit_count: int, total: int) -> float | None:
    if total == 0:
        return None
    return hit_count / total


def read_row_content(row: dict[str, Any], root: Path | None = None) -> str:
    if "content" in row:
        return str(row["content"])
    if "path" in row:
        if root is None:
            raise ValueError("root is required when reading path-backed rows")
        return (root / str(row["path"])).read_text(encoding="utf-8")
    raise ValueError("row must contain either 'content' or 'path'")


def assess_output(
    task: dict[str, Any],
    row: dict[str, Any],
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    content = read_row_content(row, root=root)
    usage = row.get("usage") or {}
    output_tokens = usage.get("output_tokens")
    if output_tokens is None:
        output_tokens = approx_token_count(content)
    input_tokens = usage.get("input_tokens")
    cached_tokens = usage.get("cached_tokens")
    effective_total_tokens = None
    if input_tokens is not None:
        effective_total_tokens = max(0, input_tokens - (cached_tokens or 0)) + output_tokens

    must_include = [str(item) for item in task.get("must_include", [])]
    exact_literals = [str(item) for item in task.get("exact_literals", [])]
    lowered = content.lower()
    must_include_hits = sum(1 for item in must_include if item.lower() in lowered)
    exact_literal_hits = sum(1 for item in exact_literals if item in content)

    result: dict[str, Any] = {
        "structured_expected": bool(row.get("structured_expected") is True),
        "transport": row.get("transport"),
        "must_include_rate": rate(must_include_hits, len(must_include)),
        "exact_literal_rate": rate(exact_literal_hits, len(exact_literals)),
        "input_tokens": input_tokens,
        "cached_tokens": cached_tokens,
        "output_tokens": output_tokens,
        "total_tokens": usage.get("total_tokens"),
        "effective_total_tokens": effective_total_tokens,
        "elapsed_ms": row.get("elapsed_ms"),
        "parse_ok": False,
        "repair_parse_ok": False,
        "mode_match": False,
        "repair_mode_match": False,
        "parse_error": None,
        "repair_parse_error": None,
        "has_audit": None,
    }

    try:
        document = parse_document(content)
    except FlintParseError as exc:
        result["parse_error"] = str(exc)
    else:
        stats = document_metrics(document, content)
        result["parse_ok"] = True
        result["mode_match"] = stats["mode"] == task.get("mode")
        result["has_audit"] = stats["has_audit"]

    if row.get("transport") == "sigil":
        repaired_content = repair_direct_flint_text(content, str(task.get("category") or ""))
    else:
        repaired_content = normalize_document_text(content)
    try:
        repaired_document = parse_document(repaired_content)
    except FlintParseError as exc:
        result["repair_parse_error"] = str(exc)
    else:
        repaired_stats = document_metrics(repaired_document, repaired_content)
        result["repair_parse_ok"] = True
        result["repair_mode_match"] = repaired_stats["mode"] == task.get("mode")

    return result


def verification_failures(
    metrics: dict[str, Any],
    *,
    min_must_include: float = 0.75,
    min_exact_literal: float = 0.75,
    require_parse: bool = True,
    require_mode_match: bool = True,
    allow_repair: bool = True,
) -> list[str]:
    failures: list[str] = []
    parse_ok = bool(metrics.get("parse_ok")) or (allow_repair and bool(metrics.get("repair_parse_ok")))
    mode_match = bool(metrics.get("mode_match")) or (allow_repair and bool(metrics.get("repair_mode_match")))
    must_include_rate = metrics.get("must_include_rate")
    exact_literal_rate = metrics.get("exact_literal_rate")

    if require_parse and not parse_ok:
        failures.append("parse")
    if require_mode_match and not mode_match:
        failures.append("mode")
    if must_include_rate is not None and must_include_rate < min_must_include:
        failures.append("must_include")
    if exact_literal_rate is not None and exact_literal_rate < min_exact_literal:
        failures.append("exact_literals")
    return failures


def verification_passes(
    metrics: dict[str, Any],
    *,
    min_must_include: float = 0.75,
    min_exact_literal: float = 0.75,
    require_parse: bool = True,
    require_mode_match: bool = True,
    allow_repair: bool = True,
) -> bool:
    return not verification_failures(
        metrics,
        min_must_include=min_must_include,
        min_exact_literal=min_exact_literal,
        require_parse=require_parse,
        require_mode_match=require_mode_match,
        allow_repair=allow_repair,
    )
