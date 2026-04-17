#!/usr/bin/env python3
"""Print the 4-way Caveman bench table (verbose / primitive / concise_json / SIGIL).

Aggregates across any number of runs per cell. File conventions:
  - opus47_<cell>.jsonl            (first run)
  - opus47_<cell>_r1.jsonl ... _rN (repeats)
Means + stdev are printed when n >= 2.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals" / "runs" / "caveman"
TASKS = ROOT / "evals" / "tasks_top_tier_holdout.jsonl"

# Map display label -> cell file prefix. SIGIL uses the wedge runs as the
# canonical multi-sample evidence; the single-run `opus47_sigil.jsonl` file
# is not included because it was overwritten by an exploratory A/B variant.
CELLS = [
    ("default (verbose)",      "opus47_verbose"),
    ("Caveman (primitive)",    "opus47_primitive"),
    ("concise + JSON control", "opus47_concise_json"),
    ("SIGIL",                  "opus47_sigil"),
]


def task_index() -> dict:
    return {str(json.loads(l)["id"]): json.loads(l) for l in TASKS.read_text().splitlines() if l.strip()}


def score_run(path: Path, tasks: dict) -> dict:
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    mi, tot, lat = [], [], []
    for r in rows:
        t = tasks[str(r["task_id"])]
        lo = r["content"].lower()
        mi.append(sum(1 for x in t["must_include"] if str(x).lower() in lo) / len(t["must_include"]))
        u = r["usage"]
        tot.append((u.get("input_tokens") or 0) + (u.get("output_tokens") or 0))
        lat.append(r.get("elapsed_ms") or 0)
    return {"must": mean(mi) * 100, "tot": mean(tot), "lat": mean(lat) / 1000}


def cell_paths(prefix: str) -> list[Path]:
    base = OUT / f"{prefix}.jsonl"
    rerun = sorted(Path(p) for p in glob.glob(str(OUT / f"{prefix}_r*.jsonl")))
    out: list[Path] = []
    if base.exists():
        out.append(base)
    out.extend(rerun)
    return out


def fmt(mean_: float, sd: float, unit: str = "") -> str:
    return f"{mean_:.1f}{unit} ± {sd:.1f}" if sd > 0 else f"{mean_:.1f}{unit}"


def main() -> int:
    tasks = task_index()
    print(f"{'variant':<24} {'n':>2} {'tokens':>14} {'latency':>14} {'must_inc':>14} {'vs verbose tok':>16} {'vs verbose lat':>16}")
    baseline: dict | None = None
    for label, prefix in CELLS:
        paths = cell_paths(prefix)
        if not paths:
            print(f"{label:<24} MISSING ({prefix})")
            continue
        scores = [score_run(p, tasks) for p in paths]
        n = len(scores)
        agg = {
            k: (mean([s[k] for s in scores]), stdev([s[k] for s in scores]) if n > 1 else 0.0)
            for k in ["must", "tot", "lat"]
        }
        if baseline is None:
            baseline = agg
            dt = dl = "—"
        else:
            dt = f"{(agg['tot'][0] - baseline['tot'][0]) / baseline['tot'][0] * 100:+.1f}%"
            dl = f"{(agg['lat'][0] - baseline['lat'][0]) / baseline['lat'][0] * 100:+.1f}%"
        print(
            f"{label:<24} {n:>2} "
            f"{fmt(agg['tot'][0], agg['tot'][1]):>14} "
            f"{fmt(agg['lat'][0], agg['lat'][1], 's'):>14} "
            f"{fmt(agg['must'][0], agg['must'][1], '%'):>14} "
            f"{dt:>16} {dl:>16}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
