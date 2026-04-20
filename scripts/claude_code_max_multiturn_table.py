#!/usr/bin/env python3
"""Aggregate multi-turn bench: per-turn and per-scenario metrics for plain vs flint.

Reads evals/runs/claude_code_max_multiturn/{plain,flint}_r*.jsonl.
Reports for each variant:
  - per-turn: ir_hit, strict_ir, out_tokens, latency, classification vs expected_shape
  - per-scenario totals: cumulative output tokens across all turns
  - overall: mean cumulative savings vs plain
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

try:
    from flint.parser import FlintParseError, parse_document
    HAS_PARSER = True
except Exception:
    HAS_PARSER = False

OUT = ROOT / "evals" / "runs" / "claude_code_max_multiturn"
TASKS = ROOT / "evals" / "claude_code_max_multiturn.jsonl"

IR_PREFIX = re.compile(r"^\s*@flint\s+v\d+\b", re.IGNORECASE)
REQUIRED_TAGS = {"G", "C", "P", "V", "A"}


def nfc(s): return unicodedata.normalize("NFC", s or "")


def is_ir(raw): return bool(IR_PREFIX.match(nfc(raw)))


def strict_pass(raw):
    if not HAS_PARSER:
        return False
    t = nfc(raw)
    try:
        doc = parse_document(t)
    except FlintParseError:
        try:
            doc = parse_document(t.rstrip() + "\n\n[AUDIT]\n[p]")
        except FlintParseError:
            return False
    if doc.header is None or doc.header.version != "v0" or doc.header.mode != "hybrid":
        return False
    return REQUIRED_TAGS.issubset({c.tag for c in doc.clauses})


def load_corpus():
    scenarios = {}
    for line in TASKS.read_text().splitlines():
        if not line.strip():
            continue
        scen = json.loads(line)
        scenarios[scen["scenario_id"]] = {t["id"]: t for t in scen["turns"]}
    return scenarios


def load_run(prefix):
    paths = sorted(OUT.glob(f"{prefix}_r*.jsonl"))
    runs = []
    for p in paths:
        runs.append([json.loads(l) for l in p.read_text().splitlines() if l.strip()])
    return runs


def variant_summary(rows, scenarios):
    # Index rows by scenario + turn
    per_turn = {}
    scen_totals = {}  # scenario_id -> cumulative output tokens
    class_hits = class_total = 0
    parse_hits = ir_hits = 0
    latencies = []
    for r in rows:
        if "error" in r:
            continue
        scen = r["scenario_id"]
        turn = r["turn_id"]
        raw = r.get("content") or ""
        usage = r.get("usage") or {}
        ot = usage.get("output_tokens") or 0
        latencies.append((r.get("elapsed_ms") or 0) / 1000)
        expected = scenarios[scen][turn]["expected_shape"]
        detected = "ir" if is_ir(raw) else "prose"
        ok = detected == expected
        class_total += 1
        if ok:
            class_hits += 1
        if is_ir(raw):
            ir_hits += 1
        if strict_pass(raw):
            parse_hits += 1
        key = (scen, turn)
        per_turn.setdefault(key, []).append({
            "out": ot, "detected": detected, "expected": expected, "ok": ok,
            "ir": is_ir(raw), "parse": strict_pass(raw),
            "lat": (r.get("elapsed_ms") or 0) / 1000,
        })
        scen_totals.setdefault(scen, 0)
        scen_totals[scen] += ot
    return {
        "per_turn": per_turn,
        "scen_totals": scen_totals,
        "class_acc": class_hits / class_total * 100 if class_total else 0,
        "ir_hit": ir_hits / class_total * 100 if class_total else 0,
        "parse_on_ir": parse_hits / ir_hits * 100 if ir_hits else 0,
        "mean_lat": mean(latencies) if latencies else 0,
        "total": sum(scen_totals.values()),
        "n": class_total,
    }


def main():
    scenarios = load_corpus()
    variants = [("plain claude", "plain"), ("flint", "flint")]
    summaries = {}
    for label, prefix in variants:
        runs = load_run(prefix)
        if not runs:
            print(f"{label}: MISSING")
            continue
        # Aggregate across runs: concat rows
        all_rows = [r for run in runs for r in run]
        summaries[label] = variant_summary(all_rows, scenarios)

    print("Per-scenario cumulative output tokens (mean across runs):")
    print(f"{'scenario':<28} {'plain':>10} {'flint':>10} {'savings':>10}")
    scen_ids = sorted({s for sm in summaries.values() for s in sm["scen_totals"]})
    n_runs = {lb: len(load_run(pr)) for lb, pr in variants}
    for sid in scen_ids:
        plain_total = summaries.get("plain claude", {}).get("scen_totals", {}).get(sid, 0)
        flint_total = summaries.get("flint", {}).get("scen_totals", {}).get(sid, 0)
        plain_mean = plain_total / max(1, n_runs["plain claude"])
        flint_mean = flint_total / max(1, n_runs["flint"])
        saving = (plain_mean - flint_mean) / plain_mean * 100 if plain_mean else 0
        print(f"{sid:<28} {plain_mean:>10.0f} {flint_mean:>10.0f} {saving:>9.0f}%")

    print()
    print("Per-turn detail (plain vs flint):")
    print(f"{'scenario':<25} {'turn':<6} {'exp':<6} {'plain':<14} {'flint':<14} {'plain_tok':>9} {'flint_tok':>9}")
    for sid in scen_ids:
        for tid in scenarios[sid]:
            expected = scenarios[sid][tid]["expected_shape"]
            plain_rows = summaries.get("plain claude", {}).get("per_turn", {}).get((sid, tid), [])
            flint_rows = summaries.get("flint", {}).get("per_turn", {}).get((sid, tid), [])
            plain_det = [r["detected"] for r in plain_rows]
            flint_det = [r["detected"] for r in flint_rows]
            plain_tok = mean([r["out"] for r in plain_rows]) if plain_rows else 0
            flint_tok = mean([r["out"] for r in flint_rows]) if flint_rows else 0
            print(f"{sid:<25} {tid:<6} {expected:<6} "
                  f"{'/'.join(plain_det):<14} {'/'.join(flint_det):<14} "
                  f"{plain_tok:>9.0f} {flint_tok:>9.0f}")

    print()
    print(f"{'variant':<16} {'n':>3} {'class_acc':>10} {'ir_hit':>9} {'parse_on_ir':>13} {'mean_lat':>10} {'total_tok':>11}")
    for label, sm in summaries.items():
        print(f"{label:<16} {sm['n']:>3} {sm['class_acc']:>9.0f}% "
              f"{sm['ir_hit']:>8.0f}% {sm['parse_on_ir']:>12.0f}% "
              f"{sm['mean_lat']:>9.1f}s {sm['total']:>11}")


if __name__ == "__main__":
    main()
