#!/usr/bin/env python3
"""Aggregate long multi-turn 4-variant bench with honest IR-only parse metrics."""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

try:
    from flint.parser import FlintParseError, parse_document

    HAS_PARSER = True
except Exception:
    HAS_PARSER = False

OUT = ROOT / "evals" / "runs" / "claude_code_max_long_multiturn_4var"
TASKS = ROOT / "evals" / "claude_code_max_long_multiturn.jsonl"

IR_PREFIX = re.compile(r"^\s*@flint\s+v\d+\b", re.IGNORECASE)
INFRA_ERROR_PREFIX = re.compile(r"^\s*(Error:|error:|Traceback)")
FENCED_CODE_BLOCK = re.compile(r"```[\w+-]*\n[\s\S]*?\n```", re.MULTILINE)
REQUIRED_TAGS = {"G", "C", "P", "V", "A"}

CELLS = [
    ("plain claude", "plain"),
    ("cccaveman", "cccaveman"),
    ("flint", "flint"),
    ("flint-mcp", "flint_mcp"),
]

PREFIX_FALLBACKS = {
    "flint": ("cccflint_pro", "cccflint"),
    "flint_mcp": ("cccflint_mcp_pro", "cccflint_mcp"),
}

RAW_COUNT_KEYS = (
    "n",
    "class_hits",
    "class_total",
    "ir_hits",
    "tool_hits",
    "ir_turn_count",
    "parse_hits",
    "must_hits",
    "must_total",
    "total_out",
    "lat_sum_s",
    "lat_n",
    "agent_cont",
    "infra_error_n",
)


def nfc(value: object) -> str:
    return unicodedata.normalize("NFC", "" if value is None else str(value))


def is_ir(raw: object) -> bool:
    return bool(IR_PREFIX.match(nfc(raw)))


def has_fenced_code(raw: object) -> bool:
    return bool(FENCED_CODE_BLOCK.search(nfc(raw)))


def strict_pass(raw: object) -> bool:
    if not HAS_PARSER:
        return False
    text = nfc(raw)
    try:
        doc = parse_document(text)
    except FlintParseError:
        try:
            doc = parse_document(text.rstrip() + "\n\n[AUDIT]\n[p]")
        except FlintParseError:
            return False
    if doc.header is None or doc.header.version != "v0" or doc.header.mode != "hybrid":
        return False
    return REQUIRED_TAGS.issubset({clause.tag for clause in doc.clauses})


def has_flint_tool(row: dict[str, object]) -> bool:
    return any("submit_flint_ir" in (tu.get("name") or "").lower() for tu in row.get("tool_uses") or [])


def has_agent_tool(row: dict[str, object]) -> bool:
    for tu in row.get("tool_uses") or []:
        name = tu.get("name") or ""
        if not name:
            continue
        lower = name.lower()
        if "submit_flint_ir" in lower:
            continue
        if name == "ToolSearch":
            continue
        return True
    return False


def render_tool_ir(tool_input: object) -> str | None:
    if not isinstance(tool_input, dict):
        return None
    if "G" not in tool_input:
        return None

    lines = [f"@flint v0 hybrid", f"G: {nfc(tool_input.get('G')).strip()}"]
    for tag in ("C", "P", "V", "A"):
        values = tool_input.get(tag)
        if values is None:
            return None
        if isinstance(values, (list, tuple)):
            atoms = [nfc(value).strip() for value in values if nfc(value).strip()]
        else:
            atoms = [nfc(values).strip()] if nfc(values).strip() else []
        if not atoms:
            return None
        lines.append(f"{tag}: {' ∧ '.join(atoms)}")

    audit = nfc(tool_input.get("audit")).strip()
    if audit:
        lines.extend(["", "[AUDIT]", audit])
    return "\n".join(lines)


def parse_hit_for_row(row: dict[str, object]) -> bool:
    raw = row.get("content")
    if raw and strict_pass(raw):
        return True
    for tool_use in row.get("tool_uses") or []:
        if "submit_flint_ir" not in (tool_use.get("name") or "").lower():
            continue
        rendered = render_tool_ir(tool_use.get("input"))
        if rendered and strict_pass(rendered):
            return True
    return False


def is_infra_error(row: dict[str, object]) -> bool:
    content = row.get("content")
    if (row.get("exit_code") or 0) != 0:
        return True
    if not content:
        return True
    if "error" in row:
        return True
    if isinstance(content, str) and INFRA_ERROR_PREFIX.match(content[:50]):
        return True
    return False


def new_counts() -> dict[str, float]:
    return {
        "n": 0,
        "class_hits": 0,
        "class_total": 0,
        "ir_hits": 0,
        "tool_hits": 0,
        "ir_turn_count": 0,
        "parse_hits": 0,
        "must_hits": 0,
        "must_total": 0,
        "total_out": 0,
        "lat_sum_s": 0.0,
        "lat_n": 0,
        "agent_cont": 0,
        "infra_error_n": 0,
    }


def merge_counts(dst: dict[str, float], src: dict[str, float]) -> dict[str, float]:
    for key in RAW_COUNT_KEYS:
        dst[key] += src[key]
    return dst


def finalize_counts(counts: dict[str, float]) -> dict[str, float | None]:
    summary: dict[str, float | None] = dict(counts)
    class_total = int(summary["class_total"])
    ir_turn_count = int(summary["ir_turn_count"])
    must_total = int(summary["must_total"])
    lat_n = int(summary["lat_n"])
    summary["class_acc"] = (summary["class_hits"] / class_total * 100) if class_total else 0.0
    summary["ir_hit"] = (summary["ir_hits"] / class_total * 100) if class_total else 0.0
    summary["tool_hit"] = (summary["tool_hits"] / class_total * 100) if class_total else 0.0
    summary["parse_on_ir_turns"] = (
        summary["parse_hits"] / ir_turn_count * 100 if ir_turn_count else None
    )
    summary["must_include"] = (summary["must_hits"] / must_total * 100) if must_total else 0.0
    summary["mean_lat"] = (summary["lat_sum_s"] / lat_n) if lat_n else 0.0
    return summary


def score_rows(rows: list[dict[str, object]], scenarios: dict[str, dict[str, dict[str, object]]]) -> dict[str, float | None]:
    counts = new_counts()
    for row in rows:
        counts["n"] += 1
        infra_error = is_infra_error(row)
        if infra_error:
            counts["infra_error_n"] += 1
        if infra_error or "error" in row:
            continue

        raw = nfc(row.get("content"))
        usage = row.get("usage") or {}
        counts["total_out"] += (usage.get("output_tokens") or 0)
        counts["lat_sum_s"] += (row.get("elapsed_ms") or 0) / 1000
        counts["lat_n"] += 1

        scenario_id = row["scenario_id"]
        turn_id = row["turn_id"]
        task = scenarios[scenario_id][turn_id]
        expected = task["expected_shape"]

        free_ir = is_ir(raw)
        tool_ir = has_flint_tool(row)
        if free_ir or tool_ir:
            detected = "ir"
        elif has_fenced_code(raw):
            detected = "prose_code"
        else:
            detected = "prose"

        counts["class_total"] += 1
        if detected == expected:
            counts["class_hits"] += 1
        if free_ir:
            counts["ir_hits"] += 1
        if tool_ir:
            counts["tool_hits"] += 1
        if detected == "ir":
            counts["ir_turn_count"] += 1
            if parse_hit_for_row(row):
                counts["parse_hits"] += 1
        if has_agent_tool(row):
            counts["agent_cont"] += 1

        must_include = task.get("must_include", [])
        if must_include:
            lowered = raw.lower()
            counts["must_hits"] += sum(1 for item in must_include if str(item).lower() in lowered)
            counts["must_total"] += len(must_include)

    return finalize_counts(counts)


def load_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_corpus(task_path: Path = TASKS) -> dict[str, dict[str, dict[str, object]]]:
    scenarios: dict[str, dict[str, dict[str, object]]] = {}
    for row in load_jsonl(Path(task_path)):
        scenarios[row["scenario_id"]] = {turn["id"]: turn for turn in row["turns"]}
    return scenarios


def load_cell(prefix: str, out_dir: Path = OUT) -> list[list[dict[str, object]]]:
    out_dir = Path(out_dir)
    candidates = (prefix,) + PREFIX_FALLBACKS.get(prefix, ())
    for candidate in candidates:
        paths = sorted(out_dir.glob(f"{candidate}_r*.jsonl"))
        if paths:
            return [load_jsonl(path) for path in paths]
    return []


def scenario_codes(scenario_ids: list[str]) -> dict[str, str]:
    return {scenario_id: f"S{index}" for index, scenario_id in enumerate(scenario_ids, start=1)}


def build_report(
    task_path: Path = TASKS,
    out_dir: Path = OUT,
    cells: list[tuple[str, str]] = CELLS,
) -> dict[str, object]:
    scenarios = load_corpus(Path(task_path))
    scenario_ids = list(scenarios.keys())
    codes = scenario_codes(scenario_ids)
    headline: dict[str, dict[str, float | None] | None] = {}
    breakdown: dict[str, dict[str, dict[str, float | None]]] = {}
    scenario_rows: list[dict[str, object]] = []

    for label, prefix in cells:
        runs = load_cell(prefix, Path(out_dir))
        if not runs:
            headline[label] = None
            breakdown[label] = {}
            continue

        all_rows = [row for run in runs for row in run]
        headline[label] = score_rows(all_rows, scenarios)

        grouped_rows = {scenario_id: [] for scenario_id in scenario_ids}
        for row in all_rows:
            scenario_id = row.get("scenario_id")
            if scenario_id in grouped_rows:
                grouped_rows[scenario_id].append(row)

        breakdown[label] = {}
        for scenario_id in scenario_ids:
            summary = score_rows(grouped_rows[scenario_id], scenarios)
            breakdown[label][scenario_id] = summary
            scenario_rows.append(
                {
                    "scenario_id": scenario_id,
                    "scenario_code": codes[scenario_id],
                    "variant": label,
                    "prefix": prefix,
                    **summary,
                }
            )

    return {
        "scenarios": scenarios,
        "scenario_ids": scenario_ids,
        "scenario_codes": codes,
        "headline": headline,
        "breakdown": breakdown,
        "scenario_rows": scenario_rows,
    }


def format_percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0f}%"


def format_ratio(numerator: float | None, denominator: float | None) -> str:
    return f"{int(numerator or 0)}/{int(denominator or 0)}"


def render_report(report: dict[str, object], cells: list[tuple[str, str]] = CELLS) -> str:
    headline = report["headline"]
    breakdown = report["breakdown"]
    scenario_ids = report["scenario_ids"]
    codes = report["scenario_codes"]

    lines: list[str] = []
    lines.append(
        f"{'variant':<20} {'n':>3} {'class_acc':>10} {'ir_hit':>9} {'tool_hit':>10} "
        f"{'parse_on_ir_turns':>18} {'infra_error_n':>14} {'must_inc':>10} "
        f"{'total_tok':>11} {'mean_lat':>10} {'agent_n':>9}"
    )
    for label, _ in cells:
        summary = headline.get(label)
        if not summary:
            lines.append(f"{label:<20} MISSING")
            continue
        lines.append(
            f"{label:<20} {int(summary['n']):>3} "
            f"{format_percent(summary['class_acc']):>10} {format_percent(summary['ir_hit']):>9} "
            f"{format_percent(summary['tool_hit']):>10} {format_percent(summary['parse_on_ir_turns']):>18} "
            f"{format_ratio(summary['infra_error_n'], summary['n']):>14} "
            f"{format_percent(summary['must_include']):>10} {int(summary['total_out']):>11} "
            f"{summary['mean_lat']:>9.1f}s {format_ratio(summary['agent_cont'], summary['n']):>9}"
        )

    lines.append("")
    lines.append("Per-scenario breakdown:")
    for scenario_id in scenario_ids:
        lines.append(f"  {codes[scenario_id]} = {scenario_id}")
    lines.append(
        f"{'scn':<3} {'variant':<20} {'class_acc':>10} {'ir_hit':>9} {'tool_hit':>10} "
        f"{'parse_on_ir_turns':>18} {'must_inc':>10} {'total_tok':>11} {'mean_lat':>10}"
    )
    for scenario_id in scenario_ids:
        code = codes[scenario_id]
        for label, _ in cells:
            summary = breakdown.get(label, {}).get(scenario_id)
            if not summary:
                lines.append(f"{code:<3} {label:<20} MISSING")
                continue
            lines.append(
                f"{code:<3} {label:<20} {format_percent(summary['class_acc']):>10} "
                f"{format_percent(summary['ir_hit']):>9} {format_percent(summary['tool_hit']):>10} "
                f"{format_percent(summary['parse_on_ir_turns']):>18} "
                f"{format_percent(summary['must_include']):>10} {int(summary['total_out']):>11} "
                f"{summary['mean_lat']:>9.1f}s"
            )

    plain = headline.get("plain claude")
    if plain:
        lines.append("")
        lines.append("vs plain claude:")
        for label, _ in cells:
            summary = headline.get(label)
            if not summary or label == "plain claude":
                continue
            dt = (
                (summary["total_out"] - plain["total_out"]) / plain["total_out"] * 100
                if plain["total_out"]
                else 0.0
            )
            dl = (
                (summary["mean_lat"] - plain["mean_lat"]) / plain["mean_lat"] * 100
                if plain["mean_lat"]
                else 0.0
            )
            dm = summary["must_include"] - plain["must_include"]
            dc = summary["class_acc"] - plain["class_acc"]
            lines.append(
                f"  {label:<20} tok {dt:+6.1f}%  lat {dl:+6.1f}%  must_inc {dm:+6.1f}pt  class {dc:+.0f}pt"
            )

    return "\n".join(lines)


def main() -> None:
    print(render_report(build_report()))


if __name__ == "__main__":
    main()
