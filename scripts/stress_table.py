#!/usr/bin/env python3
"""Summarize the stress (long-context) bench: text-sigil vs flint5-tool.

Reports both raw input tokens AND effective input tokens (accounting for cache
reads at 0.1x cost per Anthropic pricing). This is where the transport fight
actually gets decided at realistic prompt sizes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flint.eval_common import cell_run_files  # noqa: E402

OUT = ROOT / "evals" / "runs" / "stress"
TASKS = ROOT / "evals" / "tasks_stress_coding.jsonl"

CELLS = [
    ("SIGIL (text)",      "stress_sigil"),
    ("SIGIL tool-use",    "stress_tool"),
]


def tasks_index() -> dict:
    rows = {}
    for l in TASKS.read_text().splitlines():
        if not l.strip(): continue
        r = json.loads(l)
        rows[str(r["id"])] = r
    return rows


def score_run(path: Path, tasks: dict) -> dict:
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    mi, tot_raw, tot_eff, lat, sentinel, input_, cached, output = [], [], [], [], 0, [], [], []
    for r in rows:
        if r.get("sentinel"):
            sentinel += 1
            continue
        t = tasks[str(r["task_id"])]
        lo = r["content"].lower()
        mi_list = t.get("must_include", [])
        if mi_list:
            mi.append(sum(1 for x in mi_list if str(x).lower() in lo) / len(mi_list))
        u = r.get("usage") or {}
        inp = u.get("input_tokens") or 0
        out = u.get("output_tokens") or 0
        cach = u.get("cached_tokens") or 0
        # Raw total: sum of unique input + output.
        tot_raw.append(inp + out)
        # Effective cost: uncached_input + cached*0.1 + output (Anthropic pricing ratio).
        uncached = max(0, inp - cach)
        tot_eff.append(uncached + cach * 0.1 + out)
        lat.append((r.get("elapsed_ms") or 0) / 1000)
        input_.append(inp)
        cached.append(cach)
        output.append(out)
    return {
        "n_rows": len(rows),
        "sentinel": sentinel,
        "must": mean(mi) * 100 if mi else 0.0,
        "tot_raw": mean(tot_raw) if tot_raw else 0.0,
        "tot_eff": mean(tot_eff) if tot_eff else 0.0,
        "lat": mean(lat) if lat else 0.0,
        "input": mean(input_) if input_ else 0.0,
        "cached": mean(cached) if cached else 0.0,
        "output": mean(output) if output else 0.0,
    }


def fmt(m: float, s: float, unit: str = "") -> str:
    return f"{m:.0f}{unit}±{s:.0f}" if s > 0 else f"{m:.0f}{unit}"


def main() -> int:
    tasks = tasks_index()
    baseline = None
    print(
        f"{'variant':<20} {'n':>2} {'input':>8} {'cached':>8} {'output':>7} "
        f"{'raw_tot':>8} {'eff_tot':>8} {'latency':>10} {'must':>7} {'sent':>5}"
    )
    for label, cell in CELLS:
        paths = cell_run_files(OUT, cell)
        if not paths:
            print(f"{label:<20} MISSING")
            continue
        scores = [score_run(p, tasks) for p in paths]
        n = len(scores)
        agg = {k: (mean([s[k] for s in scores]), stdev([s[k] for s in scores]) if n > 1 else 0.0)
               for k in ["input","cached","output","tot_raw","tot_eff","lat","must"]}
        sent_sum = sum(s["sentinel"] for s in scores)
        d_eff = ""
        d_lat = ""
        d_must = ""
        if baseline is not None:
            d_eff = f"{(agg['tot_eff'][0]-baseline['tot_eff'][0])/baseline['tot_eff'][0]*100:+.1f}%"
            d_lat = f"{(agg['lat'][0]-baseline['lat'][0])/baseline['lat'][0]*100:+.1f}%"
            d_must = f"{agg['must'][0]-baseline['must'][0]:+.1f}pt"
        else:
            baseline = agg
        print(
            f"{label:<20} {n:>2} "
            f"{fmt(agg['input'][0], agg['input'][1]):>8} "
            f"{fmt(agg['cached'][0], agg['cached'][1]):>8} "
            f"{fmt(agg['output'][0], agg['output'][1]):>7} "
            f"{fmt(agg['tot_raw'][0], agg['tot_raw'][1]):>8} "
            f"{fmt(agg['tot_eff'][0], agg['tot_eff'][1]):>8} "
            f"{fmt(agg['lat'][0], agg['lat'][1], 's'):>10} "
            f"{fmt(agg['must'][0], agg['must'][1], '%'):>7} "
            f"{sent_sum:>5}"
        )
        if d_eff:
            print(f"{'  vs text-sigil':<20}    {'':>8} {'':>8} {'':>7} {'':>8} {d_eff:>8} {d_lat:>10} {d_must:>7}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
