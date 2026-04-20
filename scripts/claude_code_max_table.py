#!/usr/bin/env python3
"""Aggregate claude-code-max bench: plain claude vs flint wrapper.

Reads evals/runs/claude_code_max/{plain,flint}_r*.jsonl. Reports per-variant:
  - ir_hit_rate: fraction of responses starting with '@flint v\\d+' (NFC)
  - output_tokens: mean (from Claude Code usage JSON)
  - latency: mean seconds
  - must_include: mean coverage across corpus
  - class_correct: fraction of responses matching expected_shape

Also breakdowns per expected_shape subset (ir-expected vs prose-expected).
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

OUT = ROOT / "evals" / "runs" / "claude_code_max"
TASKS = ROOT / "evals" / "claude_code_max_prompts.jsonl"

IR_PREFIX = re.compile(r"^\s*@flint\s+v\d+\b", re.IGNORECASE)
REQUIRED_TAGS = {"G", "C", "P", "V", "A"}


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


def is_ir(raw: str) -> bool:
    return bool(IR_PREFIX.match(nfc(raw)))


def strict_ir_pass(raw: str) -> bool:
    if not HAS_PARSER:
        return False
    text = nfc(raw)
    try:
        doc = parse_document(text)
    except FlintParseError:
        try:
            doc = parse_document(text.rstrip() + "\n\n[AUDIT]\n[placeholder]")
        except FlintParseError:
            return False
    if doc.header is None or doc.header.version != "v0" or doc.header.mode != "hybrid":
        return False
    return REQUIRED_TAGS.issubset({c.tag for c in doc.clauses})


def load_tasks():
    return {json.loads(l)["id"]: json.loads(l) for l in TASKS.read_text().splitlines() if l.strip()}


def load_runs(prefix: str):
    paths = sorted(OUT.glob(f"{prefix}_r*.jsonl"))
    return [[json.loads(l) for l in p.read_text().splitlines() if l.strip()] for p in paths]


def score(rows, tasks):
    ir_hits = strict_hits = 0
    out_toks = []
    lat = []
    class_hits = class_total = 0
    class_hits_ir = class_total_ir = 0
    class_hits_prose = class_total_prose = 0
    must_all = []
    for r in rows:
        if "error" in r:
            continue
        raw = r.get("content") or ""
        usage = r.get("usage") or {}
        tid = r["task_id"]
        task = tasks.get(tid) or {}
        expected = task.get("expected_shape")
        must = [str(x).lower() for x in task.get("must_include", [])]
        lo = nfc(raw).lower()
        if must:
            must_all.append(sum(1 for x in must if x in lo) / len(must))
        out_toks.append(usage.get("output_tokens") or 0)
        lat.append((r.get("elapsed_ms") or 0) / 1000)
        if is_ir(raw):
            ir_hits += 1
        if strict_ir_pass(raw):
            strict_hits += 1
        if expected:
            detected = "ir" if is_ir(raw) else "prose"
            class_total += 1
            ok = detected == expected
            if ok:
                class_hits += 1
            if expected == "ir":
                class_total_ir += 1
                if ok:
                    class_hits_ir += 1
            else:
                class_total_prose += 1
                if ok:
                    class_hits_prose += 1
    n = sum(1 for r in rows if "error" not in r)
    return {
        "n": n,
        "ir_hit": ir_hits / n * 100 if n else 0.0,
        "strict": strict_hits / n * 100 if n else 0.0,
        "out": mean(out_toks) if out_toks else 0.0,
        "lat": mean(lat) if lat else 0.0,
        "must": mean(must_all) * 100 if must_all else 0.0,
        "class": class_hits / class_total * 100 if class_total else None,
        "class_ir": class_hits_ir / class_total_ir * 100 if class_total_ir else None,
        "class_prose": class_hits_prose / class_total_prose * 100 if class_total_prose else None,
    }


def agg(runs, tasks):
    scores = [score(r, tasks) for r in runs]
    if not scores:
        return None
    def m(k):
        vals = [s[k] for s in scores if s.get(k) is not None]
        return (mean(vals), stdev(vals) if len(vals) > 1 else 0.0) if vals else None
    return {k: m(k) for k in ("ir_hit", "strict", "out", "lat", "must", "class", "class_ir", "class_prose")}, len(scores)


def fmt(mv, unit=""):
    if mv is None:
        return "—"
    m_, s = mv
    return f"{m_:.0f}{unit}±{s:.0f}" if s > 0 else f"{m_:.0f}{unit}"


def main():
    tasks = load_tasks()
    variants = [("plain claude", "plain"), ("flint", "flint")]
    header = (f"{'variant':<16} {'n':>2} {'ir_hit':>8} {'strict_ir':>10} "
              f"{'out_tok':>8} {'latency':>9} {'must_inc':>9} "
              f"{'class':>8} {'class_ir':>10} {'class_prose':>12}")
    print(header)
    for label, prefix in variants:
        runs = load_runs(prefix)
        if not runs:
            print(f"{label:<16} MISSING")
            continue
        result = agg(runs, tasks)
        if result is None:
            print(f"{label:<16} empty")
            continue
        a, n = result
        print(
            f"{label:<16} {n:>2} "
            f"{fmt(a['ir_hit'], '%'):>8} "
            f"{fmt(a['strict'], '%'):>10} "
            f"{fmt(a['out']):>8} "
            f"{fmt(a['lat'], 's'):>9} "
            f"{fmt(a['must'], '%'):>9} "
            f"{fmt(a['class'], '%'):>8} "
            f"{fmt(a['class_ir'], '%'):>10} "
            f"{fmt(a['class_prose'], '%'):>12}"
        )


if __name__ == "__main__":
    main()
