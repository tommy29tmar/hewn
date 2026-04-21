#!/usr/bin/env python3
"""Aggregate 4-cell multi-turn bench: plain vs flint vs +MCP combinations.

Cells:
  plain         — baseline Anthropic default
  flint         — Flint thinking-mode prompt + drift-fix hook, no MCP
  plain_mcp     — MCP tool available, no system-prompt push
  flint_mcp     — system prompt + MCP + drift-fix hook (schema-enforced IR)

Reports per variant:
  - classification accuracy (task-shape match)
  - ir_hit: final response starts with @flint v (free-text IR)
  - tool_call_hit: submit_flint_ir was invoked at least once
  - parser-pass on IR outputs (free-text OR tool-emitted)
  - cumulative output tokens across both scenarios
  - mean latency
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

OUT = ROOT / "evals" / "runs" / "claude_code_max_4cell"
TASKS = ROOT / "evals" / "claude_code_max_multiturn.jsonl"

IR_PREFIX = re.compile(r"^\s*@flint\s+v\d+\b", re.IGNORECASE)
REQUIRED_TAGS = {"G", "C", "P", "V", "A"}

CELLS = [
    ("plain claude",     "plain"),
    ("flint",            "flint"),
    ("plain + MCP",      "plain_mcp"),
    ("flint + MCP",      "flint_mcp"),
]

PREFIX_FALLBACKS = {
    "flint": ("cccflint_pro", "cccflint"),
    "flint_mcp": ("cccflint_mcp_pro", "cccflint_mcp"),
}


def nfc(s): return unicodedata.normalize("NFC", s or "")


def is_ir(raw): return bool(IR_PREFIX.match(nfc(raw)))


def shape_matches(detected: str, expected: object) -> bool:
    expected_shape = nfc(str(expected) if expected is not None else "")
    if detected == expected_shape:
        return True
    return detected == "prose" and expected_shape.startswith("prose")


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


def has_flint_tool_call(row):
    for tu in row.get("tool_uses") or []:
        name = (tu.get("name") or "").lower()
        if "submit_flint_ir" in name:
            return True
    return False


def has_non_flint_tool_call(row):
    """Agent-mode contamination: Bash, Read, Write, Edit, Grep, Glob, Task, other MCP tools."""
    for tu in row.get("tool_uses") or []:
        name = (tu.get("name") or "")
        lower = name.lower()
        if not name:
            continue
        # Allowed: Flint IR tool, ToolSearch (meta, finds tools without executing)
        if "submit_flint_ir" in lower:
            continue
        if name == "ToolSearch":
            continue
        return True
    return False


def load_corpus():
    scenarios = {}
    for line in TASKS.read_text().splitlines():
        if not line.strip():
            continue
        scen = json.loads(line)
        scenarios[scen["scenario_id"]] = {t["id"]: t for t in scen["turns"]}
    return scenarios


def load_cell(prefix):
    candidates = (prefix,) + PREFIX_FALLBACKS.get(prefix, ())
    for candidate in candidates:
        paths = sorted(OUT.glob(f"{candidate}_r*.jsonl"))
        if paths:
            runs = []
            for p in paths:
                runs.append([json.loads(l) for l in p.read_text().splitlines() if l.strip()])
            return runs
    return []


def score_rows(rows, scenarios):
    ir_hits = tool_hits = parse_hits = class_hits = class_total = 0
    agent_contaminated = 0
    total_out = 0
    clean_out = 0  # tokens from turns with no non-flint tool use
    latencies = []
    scen_totals = {}
    clean_scen_totals = {}
    per_turn = {}
    for r in rows:
        if "error" in r:
            continue
        raw = r.get("content") or ""
        usage = r.get("usage") or {}
        out_tok = usage.get("output_tokens") or 0
        total_out += out_tok
        latencies.append((r.get("elapsed_ms") or 0) / 1000)
        scen = r["scenario_id"]
        tid = r["turn_id"]
        scen_totals.setdefault(scen, 0)
        scen_totals[scen] += out_tok
        expected = scenarios[scen][tid]["expected_shape"]

        free_ir = is_ir(raw)
        tool_ir = has_flint_tool_call(r)
        agent_tool = has_non_flint_tool_call(r)
        detected = "ir" if (free_ir or tool_ir) else "prose"
        class_total += 1
        if shape_matches(detected, expected):
            class_hits += 1
        if free_ir:
            ir_hits += 1
        if tool_ir:
            tool_hits += 1
        if strict_pass(raw):
            parse_hits += 1
        if agent_tool:
            agent_contaminated += 1
        else:
            clean_out += out_tok
            clean_scen_totals.setdefault(scen, 0)
            clean_scen_totals[scen] += out_tok
        per_turn.setdefault((scen, tid), []).append({
            "out": out_tok, "detected": detected, "free_ir": free_ir, "tool_ir": tool_ir,
            "agent": agent_tool, "parse": strict_pass(raw),
        })
    return {
        "n": class_total,
        "class_acc": class_hits / class_total * 100 if class_total else 0,
        "ir_hit": ir_hits / class_total * 100 if class_total else 0,
        "tool_hit": tool_hits / class_total * 100 if class_total else 0,
        "parse": parse_hits / class_total * 100 if class_total else 0,
        "total_out": total_out,
        "clean_out": clean_out,  # tokens from agent-free turns only
        "agent_contaminated": agent_contaminated,
        "mean_lat": mean(latencies) if latencies else 0,
        "scen_totals": scen_totals,
        "clean_scen_totals": clean_scen_totals,
        "per_turn": per_turn,
    }


def main():
    scenarios = load_corpus()
    summaries = {}
    for label, prefix in CELLS:
        runs = load_cell(prefix)
        if not runs:
            print(f"{label}: MISSING")
            summaries[label] = None
            continue
        all_rows = [r for run in runs for r in run]
        summaries[label] = score_rows(all_rows, scenarios)

    # Per-scenario cumulative tokens
    print("Per-scenario cumulative output tokens (sum across runs):")
    print(f"{'scenario':<28} " + "".join(f"{label:<17}" for label,_ in CELLS))
    scen_ids = sorted({s for sm in summaries.values() if sm for s in sm["scen_totals"]})
    for sid in scen_ids:
        row = f"{sid:<28} "
        for label, _ in CELLS:
            sm = summaries.get(label)
            tot = sm["scen_totals"].get(sid, 0) if sm else 0
            row += f"{tot:<17}"
        print(row)

    # Overall summary
    print()
    print(f"{'variant':<18} {'n':>3} {'class_acc':>10} {'ir_hit':>9} {'tool_hit':>10} "
          f"{'parse_%':>9} {'total_tok':>11} {'clean_tok':>11} {'agent_n':>8} {'mean_lat':>9}")
    for label, _ in CELLS:
        sm = summaries.get(label)
        if not sm:
            print(f"{label:<18} MISSING")
            continue
        print(f"{label:<18} {sm['n']:>3} "
              f"{sm['class_acc']:>9.0f}% {sm['ir_hit']:>8.0f}% {sm['tool_hit']:>9.0f}% "
              f"{sm['parse']:>8.0f}% {sm['total_out']:>11} {sm['clean_out']:>11} "
              f"{sm['agent_contaminated']:>7}/{sm['n']} {sm['mean_lat']:>8.1f}s")
    print()
    print("total_tok = all turns incl. agent-contaminated. clean_tok = turns with no non-flint tools.")
    print("agent_n = count of turns that called Bash/Read/Write/Edit/Grep/Glob/Task/other-MCP (invalid for compression metric).")

    # Per-turn detail: did IR emit happen (free or tool)?
    print()
    print("Per-turn IR signal (✓ = IR emitted, via free-text 'F' or tool 'T'):")
    header = f"{'scenario':<22} {'turn':<5} {'exp':<6}"
    for label, _ in CELLS:
        header += f"  {label:<14}"
    print(header)
    for sid in scen_ids:
        for tid in scenarios[sid]:
            expected = scenarios[sid][tid]["expected_shape"]
            row = f"{sid:<22} {tid:<5} {expected:<6}"
            for label, _ in CELLS:
                sm = summaries.get(label)
                if not sm:
                    row += f"  {'—':<14}"
                    continue
                samples = sm["per_turn"].get((sid, tid), [])
                if not samples:
                    row += f"  {'—':<14}"
                    continue
                # aggregate across runs
                free_any = sum(1 for s in samples if s["free_ir"])
                tool_any = sum(1 for s in samples if s["tool_ir"])
                n = len(samples)
                sig = ""
                if free_any:
                    sig += f"F{free_any}/{n} "
                if tool_any:
                    sig += f"T{tool_any}/{n} "
                if not sig:
                    sig = "prose "
                row += f"  {sig.strip():<14}"
            print(row)


if __name__ == "__main__":
    main()
