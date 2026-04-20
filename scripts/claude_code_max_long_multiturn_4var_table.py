#!/usr/bin/env python3
"""Aggregate long multi-turn 4-variant bench (plain, cccaveman, flint, flint-mcp)."""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path
from statistics import mean

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
REQUIRED_TAGS = {"G", "C", "P", "V", "A"}

CELLS = [
    ("plain claude",     "plain"),
    ("cccaveman",        "cccaveman"),
    ("flint",     "flint"),
    ("flint-mcp", "flint_mcp"),
]


def nfc(s): return unicodedata.normalize("NFC", s or "")


def is_ir(raw): return bool(IR_PREFIX.match(nfc(raw)))


def strict_pass(raw):
    if not HAS_PARSER: return False
    text = nfc(raw)
    try: doc = parse_document(text)
    except FlintParseError:
        try: doc = parse_document(text.rstrip() + "\n\n[AUDIT]\n[p]")
        except FlintParseError: return False
    if doc.header is None or doc.header.version != "v0" or doc.header.mode != "hybrid": return False
    return REQUIRED_TAGS.issubset({c.tag for c in doc.clauses})


def has_flint_tool(row):
    return any("submit_flint_ir" in (tu.get("name") or "").lower() for tu in row.get("tool_uses") or [])


def has_agent_tool(row):
    for tu in row.get("tool_uses") or []:
        name = (tu.get("name") or "")
        if not name: continue
        if "submit_flint_ir" in name.lower(): continue
        if name == "ToolSearch": continue
        return True
    return False


def load_corpus():
    scenarios = {}
    for line in TASKS.read_text().splitlines():
        if not line.strip(): continue
        s = json.loads(line)
        scenarios[s["scenario_id"]] = {t["id"]: t for t in s["turns"]}
    return scenarios


def load_cell(prefix):
    paths = sorted(OUT.glob(f"{prefix}_r*.jsonl"))
    return [[json.loads(l) for l in p.read_text().splitlines() if l.strip()] for p in paths]


def score(rows, scenarios):
    n = ir_hits = tool_hits = parse_hits = class_hits = total_out = agent_cont = 0
    must_hits = must_total = 0
    latencies = []
    for r in rows:
        if "error" in r: continue
        raw = r.get("content") or ""
        u = r.get("usage") or {}
        ot = u.get("output_tokens") or 0
        total_out += ot
        latencies.append((r.get("elapsed_ms") or 0) / 1000)
        scen, tid = r["scenario_id"], r["turn_id"]
        task = scenarios[scen][tid]
        expected = task["expected_shape"]
        free_ir = is_ir(raw)
        tool_ir = has_flint_tool(r)
        detected = "ir" if (free_ir or tool_ir) else "prose"
        n += 1
        if detected == expected: class_hits += 1
        if free_ir: ir_hits += 1
        if tool_ir: tool_hits += 1
        if strict_pass(raw): parse_hits += 1
        if has_agent_tool(r): agent_cont += 1
        # must_include on content (case-insensitive substring)
        must = task.get("must_include", [])
        if must:
            lo = nfc(raw).lower()
            h = sum(1 for x in must if str(x).lower() in lo)
            must_hits += h
            must_total += len(must)
    return {
        "n": n,
        "class_acc": class_hits / n * 100 if n else 0,
        "ir_hit": ir_hits / n * 100 if n else 0,
        "tool_hit": tool_hits / n * 100 if n else 0,
        "parse": parse_hits / n * 100 if n else 0,
        "total_out": total_out,
        "mean_lat": mean(latencies) if latencies else 0,
        "must_include": must_hits / must_total * 100 if must_total else 0,
        "agent_cont": agent_cont,
    }


def main():
    scenarios = load_corpus()
    summaries = {}
    for label, prefix in CELLS:
        runs = load_cell(prefix)
        if not runs:
            summaries[label] = None
            continue
        all_rows = [r for run in runs for r in run]
        summaries[label] = score(all_rows, scenarios)

    # Headline table
    print(f"{'variant':<20} {'n':>3} {'class_acc':>10} {'ir_hit':>9} {'tool_hit':>10} "
          f"{'parse_%':>9} {'must_inc':>10} {'total_tok':>11} {'mean_lat':>10} {'agent_n':>9}")
    for label, _ in CELLS:
        s = summaries.get(label)
        if not s:
            print(f"{label:<20} MISSING")
            continue
        print(f"{label:<20} {s['n']:>3} {s['class_acc']:>9.0f}% {s['ir_hit']:>8.0f}% "
              f"{s['tool_hit']:>9.0f}% {s['parse']:>8.0f}% {s['must_include']:>9.0f}% "
              f"{s['total_out']:>11} {s['mean_lat']:>9.1f}s {s['agent_cont']:>7}/{s['n']}")

    # Delta vs plain
    plain = summaries.get("plain claude")
    if plain:
        print()
        print("vs plain claude:")
        for label, _ in CELLS:
            s = summaries.get(label)
            if not s or label == "plain claude": continue
            dt = (s['total_out'] - plain['total_out']) / plain['total_out'] * 100
            dl = (s['mean_lat'] - plain['mean_lat']) / plain['mean_lat'] * 100 if plain['mean_lat'] else 0
            dm = s['must_include'] - plain['must_include']
            print(f"  {label:<20} tok {dt:+6.1f}%  lat {dl:+6.1f}%  must_inc {dm:+6.1f}pt  class +{s['class_acc']-plain['class_acc']:.0f}pt")


if __name__ == "__main__":
    main()
