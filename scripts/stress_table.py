#!/usr/bin/env python3
"""Aggregate stress bench table: verbose vs Caveman vs Flint on long-context tasks.

Reads evals/runs/stress/opus47_stress_{verbose,caveman,flintnew,flintthinking}_r*.jsonl.
Reports output tokens, cache-adjusted effective tokens, latency,
must_include coverage, raw IR leak rate, strict IR pass rate, and
exploded IR rate. Deltas computed vs verbose Claude baseline.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flint.eval_common import cell_run_files  # noqa: E402
from flint.parser import FlintParseError, parse_document  # noqa: E402

OUT = ROOT / "evals" / "runs" / "stress"
TASKS = ROOT / "evals" / "tasks_stress_coding.jsonl"

CELLS = [
    ("verbose Claude",      "stress_verbose"),
    ("Caveman (primitive)", "stress_caveman"),
    ("Flint",               "stress_flintnew"),
    ("Flint (thinking)",    "stress_flintthinking"),
]

REQUIRED_TAGS = {"G", "C", "P", "V", "A"}
IR_PREFIX = re.compile(r"^\s*@flint\s+v\d+\b", re.IGNORECASE)
ATOM_SPLIT = re.compile(r"[∧\s]+")


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def task_index() -> dict:
    tasks: dict[str, dict] = {}
    for line in TASKS.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        tasks[str(row["id"])] = row
    return tasks


def _parse_strict_ir(raw: str):
    text = nfc(raw)
    try:
        doc = parse_document(text)
    except FlintParseError:
        try:
            doc = parse_document(text.rstrip() + "\n\n[AUDIT]\n[placeholder]")
        except FlintParseError:
            return None
    if doc.header is None or doc.header.version != "v0" or doc.header.mode != "hybrid":
        return None
    if not REQUIRED_TAGS.issubset({c.tag for c in doc.clauses}):
        return None
    return doc


def strict_ir_pass(raw: str) -> bool:
    return _parse_strict_ir(raw) is not None


def is_exploded_document(doc) -> bool:
    atom_counts = []
    for clause in doc.clauses:
        atoms = [part for part in ATOM_SPLIT.split(clause.raw.strip()) if part]
        atom_counts.append(len(atoms))
    return any(count >= 10 for count in atom_counts) and sum(1 for count in atom_counts if count <= 2) >= 2


def score_run(path: Path, tasks: dict) -> dict:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    mi, out, eff, lat = [], [], [], []
    strict_hits = ir_hits = exploded_hits = 0
    for row in rows:
        task = tasks[str(row["task_id"])]
        raw = row.get("content") or ""
        lowered = nfc(raw).lower()
        must_include = [str(item).lower() for item in task.get("must_include", [])]
        mi.append(sum(1 for item in must_include if item in lowered) / len(must_include) if must_include else 0.0)
        usage = row.get("usage") or {}
        input_tokens = usage.get("input_tokens") or 0
        output_tokens = usage.get("output_tokens") or 0
        cached_tokens = usage.get("cached_tokens") or 0
        out.append(output_tokens)
        eff.append(max(0, input_tokens - cached_tokens) + cached_tokens * 0.1 + output_tokens)
        lat.append((row.get("elapsed_ms") or 0) / 1000)
        if IR_PREFIX.match(nfc(raw)):
            ir_hits += 1
        doc = _parse_strict_ir(raw)
        if doc is not None:
            strict_hits += 1
            if is_exploded_document(doc):
                exploded_hits += 1
    strict_total = strict_hits
    total = len(rows)
    return {
        "must": mean(mi) * 100 if mi else 0.0,
        "out": mean(out) if out else 0.0,
        "eff": mean(eff) if eff else 0.0,
        "lat": mean(lat) if lat else 0.0,
        "strict": strict_hits / total * 100 if total else 0.0,
        "ir_leak": ir_hits / total * 100 if total else 0.0,
        "exploded": exploded_hits / strict_total * 100 if strict_total else 0.0,
    }


def fmt(m: float, s: float, unit: str = "") -> str:
    return f"{m:.0f}{unit}±{s:.0f}" if s > 0 else f"{m:.0f}{unit}"


def maybe_fmt(metric: tuple[float, float] | None, unit: str = "") -> str:
    if metric is None:
        return "—"
    return fmt(metric[0], metric[1], unit)


def main() -> int:
    tasks = task_index()
    header = (f"{'variant':<22} {'n':>2} {'output':>9} {'eff_total':>11} "
              f"{'latency':>10} {'must_inc':>10} {'strict_ir':>10} {'ir_leak':>9} "
              f"{'exploded_ir':>12} {'vs verbose out':>16} {'vs verbose lat':>16}")
    print(header)
    baseline: dict | None = None
    for label, cell in CELLS:
        paths = cell_run_files(OUT, cell)
        if not paths:
            print(f"{label:<22} MISSING ({cell})")
            continue
        scores = [score_run(path, tasks) for path in paths]
        n = len(scores)
        agg = {key: (mean(score[key] for score in scores),
                     stdev(score[key] for score in scores) if n > 1 else 0.0)
               for key in ("must", "out", "eff", "lat", "strict", "ir_leak", "exploded")}
        if baseline is None:
            baseline = agg
            dout = dlat = "—"
        else:
            dout = f"{(agg['out'][0] - baseline['out'][0]) / baseline['out'][0] * 100:+.1f}%"
            dlat = f"{(agg['lat'][0] - baseline['lat'][0]) / baseline['lat'][0] * 100:+.1f}%"
        show_structural = cell in {"stress_flintnew", "stress_flintthinking"}
        strict_cell = maybe_fmt(agg["strict"], "%") if show_structural else "—"
        exploded_cell = maybe_fmt(agg["exploded"], "%") if show_structural else "—"
        print(
            f"{label:<22} {n:>2} "
            f"{fmt(agg['out'][0], agg['out'][1]):>9} "
            f"{fmt(agg['eff'][0], agg['eff'][1]):>11} "
            f"{fmt(agg['lat'][0], agg['lat'][1], 's'):>10} "
            f"{fmt(agg['must'][0], agg['must'][1], '%'):>10} "
            f"{strict_cell:>10} "
            f"{fmt(agg['ir_leak'][0], agg['ir_leak'][1], '%'):>9} "
            f"{exploded_cell:>12} "
            f"{dout:>16} {dlat:>16}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
