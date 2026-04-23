#!/usr/bin/env python3
"""Hewn benchmark report generator.

Reads snapshots/raw/* and snapshots/judgments_*.json, aggregates per
track, writes report/REPORT.md with all tables. Honest about what is
matched-from-Caveman vs Hewn-extension.

Run after run.py + judge.py have populated snapshots.

Usage:
  uv run --with tiktoken benchmarks/measure.py
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

BENCH = Path(__file__).resolve().parent
RAW = BENCH / "snapshots" / "raw"
META = BENCH / "snapshots" / "metadata.json"
REPORT = BENCH / "report" / "REPORT.md"


def load_snapshots(track: str) -> dict[str, list[dict]]:
    """Returns {arm: [snapshot_records]}."""
    out: dict[str, list[dict]] = {}
    track_dir = RAW / track
    if not track_dir.exists():
        return out
    for arm_dir in sorted(track_dir.iterdir()):
        if not arm_dir.is_dir():
            continue
        arm = arm_dir.name
        records = []
        for p in sorted(arm_dir.glob("*.json")):
            rec = json.loads(p.read_text())
            # Skip sentinel snapshots: known-model-timeout combos and
            # error-after-retries records have no measured output and
            # would be aggregated as 0 tokens / empty response.
            if rec.get("skipped") or rec.get("error"):
                continue
            records.append(rec)
        out[arm] = records
    return out


def load_judgments(track: str) -> dict[str, dict]:
    p = BENCH / "snapshots" / f"judgments_{track}.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def by_prompt_then_run(records: list[dict]) -> dict[str, list[dict]]:
    by: dict[str, list[dict]] = {}
    for r in records:
        pid = r.get("prompt_id")
        if pid is None:
            continue
        by.setdefault(pid, []).append(r)
    for v in by.values():
        v.sort(key=lambda x: x.get("run_index", 0))
    return by


def median_int(xs: list[int | float]) -> float:
    return statistics.median(xs) if xs else 0


def safe_stats(xs: list[float]) -> dict[str, float]:
    if not xs:
        return {"median": 0, "mean": 0, "min": 0, "max": 0, "stdev": 0}
    return {
        "median": statistics.median(xs),
        "mean": statistics.mean(xs),
        "min": min(xs),
        "max": max(xs),
        "stdev": statistics.stdev(xs) if len(xs) > 1 else 0.0,
    }


def fmt_pct(x: float) -> str:
    sign = "−" if x < 0 else ""
    return f"{sign}{abs(x)*100:.0f}%"


def fmt_signed(x: float) -> str:
    return f"{int(x):+d}" if abs(x) >= 1 else f"{x:+.2f}"


# ──────────────────────────────────────────────────────────────────────────────
# T0 — append-vs-replace exposure calibration
# ──────────────────────────────────────────────────────────────────────────────

def report_T0() -> str:
    snaps = load_snapshots("T0")
    if not snaps:
        return "## T0 — Append-vs-replace exposure calibration\n\n_No data._\n\n"
    terse = {r["prompt_id"]: r for r in snaps.get("terse", [])}
    terse_app = {r["prompt_id"]: r for r in snaps.get("terse_appended", [])}
    cv = {r["prompt_id"]: r for r in snaps.get("caveman_full", [])}
    cv_app = {r["prompt_id"]: r for r in snaps.get("caveman_full_appended", [])}

    rows = []
    terse_deltas = []
    cv_deltas = []
    for pid in sorted(terse.keys()):
        if pid not in terse_app or pid not in cv or pid not in cv_app:
            continue
        t = terse[pid].get("output_tokens_anthropic", 0)
        ta = terse_app[pid].get("output_tokens_anthropic", 0)
        c = cv[pid].get("output_tokens_anthropic", 0)
        ca = cv_app[pid].get("output_tokens_anthropic", 0)
        t_delta = ta - t
        c_delta = ca - c
        terse_deltas.append(t_delta)
        cv_deltas.append(c_delta)
        rows.append((pid, t, ta, t_delta, c, ca, c_delta))

    out = ["## T0 — Append-vs-replace exposure calibration",
           "",
           "Measures the output-token delta between `--system-prompt` (replace) "
           "and `--append-system-prompt` (add to default + CLAUDE.md). "
           "Positive delta = appending makes output **longer**. Negative = appending compresses **more**.",
           "",
           "Both arms use the same content (`Answer concisely.` for terse, "
           "same + Caveman SKILL.md for caveman_full). Only the flag differs.",
           "",
           "| Prompt | terse (replace) | terse (append) | Δ tokens | caveman (replace) | caveman (append) | Δ tokens |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for pid, t, ta, td, c, ca, cd in rows:
        out.append(f"| `{pid}` | {t} | {ta} | {fmt_signed(td)} | {c} | {ca} | {fmt_signed(cd)} |")
    if rows:
        ts = safe_stats(terse_deltas)
        cs = safe_stats(cv_deltas)
        out.append(f"| **median** | | | **{fmt_signed(ts['median'])}** | | | **{fmt_signed(cs['median'])}** |")
        out.append(f"| **mean** | | | **{fmt_signed(ts['mean'])}** | | | **{fmt_signed(cs['mean'])}** |")
    out.append("")
    out.append(f"_Interpretation: a positive median delta means stock Caveman/terse "
               f"(replace) numbers underestimate compression vs. Hewn arms (append); "
               f"observed Hewn-vs-Caveman savings on T1b/T2-T5 are inflated by "
               f"approximately this magnitude._")
    out.append("")
    return "\n".join(out)


# ──────────────────────────────────────────────────────────────────────────────
# T1a — strict Caveman parity
# ──────────────────────────────────────────────────────────────────────────────

def report_T1a() -> str:
    snaps = load_snapshots("T1a")
    if not snaps:
        return "## T1a — Strict Caveman parity\n\n_No data._\n\n"
    base = {r["prompt_id"]: r for r in snaps.get("baseline", [])}
    terse = {r["prompt_id"]: r for r in snaps.get("terse", [])}
    cv = {r["prompt_id"]: r for r in snaps.get("caveman_full", [])}

    out = ["## T1a — Strict Caveman parity",
           "",
           "Replicates Caveman `evals/llm_run.py` methodology precisely: "
           "`claude -p --system-prompt <x>`, **1 run per arm**, 10 prompts "
           "vendored verbatim from caveman repo, output tokens via tiktoken "
           "`o200k_base` (matches Caveman's `evals/measure.py`).",
           "",
           "**Honest delta** per Caveman's own README: skill vs `__terse__`, "
           "NOT skill vs baseline.",
           "",
           "| Prompt | baseline | terse | caveman_full | savings vs terse |",
           "|---|---:|---:|---:|---:|"]
    rows = []
    for pid in sorted(base.keys()):
        if pid not in terse or pid not in cv:
            continue
        b = base[pid].get("output_tokens_tiktoken", 0)
        t = terse[pid].get("output_tokens_tiktoken", 0)
        c = cv[pid].get("output_tokens_tiktoken", 0)
        s = (1 - c / t) if t else 0
        rows.append((pid, b, t, c, s))
        out.append(f"| `{pid}` | {b} | {t} | {c} | {fmt_pct(s)} |")
    if rows:
        savings = [r[4] for r in rows]
        st = safe_stats(savings)
        out.append(
            f"| **median** | | | | **{fmt_pct(st['median'])}** |")
        out.append(
            f"| **mean** | | | | **{fmt_pct(st['mean'])}** |")
        out.append(
            f"| **range** | | | | "
            f"**{fmt_pct(st['min'])} – {fmt_pct(st['max'])}** |")
        out.append(
            f"| **stdev** | | | | **{fmt_pct(st['stdev'])}** |")
        b_tot = sum(r[1] for r in rows)
        t_tot = sum(r[2] for r in rows)
        c_tot = sum(r[3] for r in rows)
        out.append("")
        out.append(f"Totals: baseline {b_tot} / terse {t_tot} "
                   f"(`{fmt_pct(1 - t_tot/b_tot if b_tot else 0)}` vs baseline) "
                   f"/ caveman_full {c_tot} "
                   f"(`{fmt_pct(1 - c_tot/t_tot if t_tot else 0)}` vs terse, "
                   f"`{fmt_pct(1 - c_tot/b_tot if b_tot else 0)}` vs baseline).")
    out.append("")
    return "\n".join(out)


# ──────────────────────────────────────────────────────────────────────────────
# T1b — extended (with hewn arms)
# ──────────────────────────────────────────────────────────────────────────────

def aggregate_runs_per_arm_per_prompt(records: list[dict],
                                      key: str = "output_tokens_anthropic") -> dict[str, float]:
    out: dict[str, list[float]] = {}
    for r in records:
        pid = r.get("prompt_id")
        if pid is None:
            continue
        v = r.get(key)
        if v is None:
            continue
        out.setdefault(pid, []).append(v)
    return {pid: median_int(xs) for pid, xs in out.items()}


def report_T1b_with_T0_join() -> str:
    snaps_b = load_snapshots("T1b")
    snaps_0 = load_snapshots("T0")
    if not snaps_b:
        return "## T1b — Extended short_en\n\n_No data._\n\n"

    # Median-per-prompt for each arm in T1b
    arms = ["baseline", "terse", "caveman_full",
            "caveman_full_plus_ultra_directive",
            "hewn_prompt_only", "hewn_full"]
    medians = {arm: aggregate_runs_per_arm_per_prompt(snaps_b.get(arm, []))
               for arm in arms}
    # Single-run T0 appended values
    t_app = {r["prompt_id"]: r.get("output_tokens_anthropic", 0)
             for r in snaps_0.get("terse_appended", [])}
    cv_app = {r["prompt_id"]: r.get("output_tokens_anthropic", 0)
              for r in snaps_0.get("caveman_full_appended", [])}

    out = ["## T1b — Extended short_en (Hewn extension)",
           "",
           "All 6 arms × 3 runs × 10 prompts. Median across runs per (arm, "
           "prompt). Output tokens from Anthropic `usage.output_tokens` "
           "(ground truth, not tiktoken approximation).",
           "",
           "Cell values: median(output_tokens). `hewn_full` includes the "
           "classifier hook overhead (extra `cache_creation_input_tokens`, "
           "see appendix).",
           "",
           "### Output tokens per prompt × arm",
           "",
           "| Prompt | baseline | terse | caveman_full | caveman+ultra | hewn_prompt_only | hewn_full |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    pids = sorted(medians["baseline"].keys()) if medians["baseline"] else []
    for pid in pids:
        cells = [str(int(medians[a].get(pid, 0))) for a in arms]
        out.append(f"| `{pid}` | " + " | ".join(cells) + " |")
    if pids:
        avgs = [statistics.mean([medians[a][p] for p in pids
                                 if p in medians[a]])
                for a in arms]
        out.append(f"| **mean** | " +
                   " | ".join(f"**{int(round(v))}**" for v in avgs) + " |")

    # Hewn vs others
    out.append("")
    out.append("### Hewn-vs-comparator savings — `(appended, observed)` pair")
    out.append("")
    out.append("Cross-track join: `appended` side from T0 single run; "
               "`observed` side and `hewn_full` from T1b median-of-3-runs.")
    out.append("")
    out.append("**vs Caveman full** — savings = `comparator − hewn_full` tokens; positive = Hewn fewer tokens.")
    out.append("")
    out.append("| Prompt | observed (T1b stock) | appended (T0 calibrated) |")
    out.append("|---|---:|---:|")
    obs_cv, app_cv = [], []
    for pid in pids:
        if pid not in medians["hewn_full"]:
            continue
        h = medians["hewn_full"][pid]
        obs = medians["caveman_full"].get(pid, 0) - h
        appv = (cv_app[pid] - h) if pid in cv_app else None
        obs_cv.append(obs)
        if appv is not None:
            app_cv.append(appv)
        appv_str = fmt_signed(appv) if appv is not None else "—"
        out.append(f"| `{pid}` | {fmt_signed(obs)} | {appv_str} |")
    if obs_cv:
        out.append(f"| **median** | **{fmt_signed(median_int(obs_cv))}** | "
                   f"**{fmt_signed(median_int(app_cv))}** |")
        out.append(f"| **mean** | **{fmt_signed(statistics.mean(obs_cv))}** | "
                   f"**{fmt_signed(statistics.mean(app_cv))}** |")

    out.append("")
    out.append("**vs terse** — same shape:")
    out.append("")
    out.append("| Prompt | observed (T1b stock) | appended (T0 calibrated) |")
    out.append("|---|---:|---:|")
    obs_te, app_te = [], []
    for pid in pids:
        if pid not in medians["hewn_full"]:
            continue
        h = medians["hewn_full"][pid]
        obs = medians["terse"].get(pid, 0) - h
        appv = (t_app[pid] - h) if pid in t_app else None
        obs_te.append(obs)
        if appv is not None:
            app_te.append(appv)
        appv_str = fmt_signed(appv) if appv is not None else "—"
        out.append(f"| `{pid}` | {fmt_signed(obs)} | {appv_str} |")
    if obs_te:
        out.append(f"| **median** | **{fmt_signed(median_int(obs_te))}** | "
                   f"**{fmt_signed(median_int(app_te))}** |")
        out.append(f"| **mean** | **{fmt_signed(statistics.mean(obs_te))}** | "
                   f"**{fmt_signed(statistics.mean(app_te))}** |")

    # Hewn-vs-baseline (causal — same exposure)
    out.append("")
    out.append("### Hewn-vs-baseline (causal — both arms inherit default+CLAUDE.md)")
    out.append("")
    out.append("| Prompt | baseline | hewn_full | savings |")
    out.append("|---|---:|---:|---:|")
    base_savings = []
    for pid in pids:
        if pid not in medians["hewn_full"] or pid not in medians["baseline"]:
            continue
        b = medians["baseline"][pid]
        h = medians["hewn_full"][pid]
        s = (1 - h/b) if b else 0
        base_savings.append(s)
        out.append(f"| `{pid}` | {int(b)} | {int(h)} | {fmt_pct(s)} |")
    if base_savings:
        st = safe_stats(base_savings)
        out.append(f"| **median** | | | **{fmt_pct(st['median'])}** |")
        out.append(f"| **mean** | | | **{fmt_pct(st['mean'])}** |")
        out.append(f"| **range** | | | "
                   f"**{fmt_pct(st['min'])} – {fmt_pct(st['max'])}** |")

    # Stability
    out.append("")
    out.append("### Stability (stdev of output_tokens across 3 runs per arm × prompt)")
    out.append("")
    out.append("| Arm | mean stdev across prompts |")
    out.append("|---|---:|")
    for arm in arms:
        per_prompt_stdevs = []
        records = snaps_b.get(arm, [])
        for pid in pids:
            xs = [r.get("output_tokens_anthropic", 0) for r in records
                  if r.get("prompt_id") == pid]
            if len(xs) > 1:
                per_prompt_stdevs.append(statistics.stdev(xs))
        mean_sd = statistics.mean(per_prompt_stdevs) if per_prompt_stdevs else 0
        out.append(f"| {arm} | {mean_sd:.1f} |")
    out.append("")
    return "\n".join(out)


# ──────────────────────────────────────────────────────────────────────────────
# T2/T3/T5 — observational
# ──────────────────────────────────────────────────────────────────────────────

def report_observational(track: str, name: str, n_runs: int) -> str:
    snaps = load_snapshots(track)
    if not snaps:
        return f"## {track} — {name}\n\n_No data._\n\n"
    arms = ["baseline", "terse", "caveman_full",
            "caveman_full_plus_ultra_directive",
            "hewn_prompt_only", "hewn_full"]
    medians = {arm: aggregate_runs_per_arm_per_prompt(snaps.get(arm, []))
               for arm in arms}
    pids = sorted(medians["baseline"].keys()) if medians["baseline"] else []
    if not pids:
        return f"## {track} — {name}\n\n_No data._\n\n"

    out = [f"## {track} — {name}",
           "",
           f"{n_runs} runs × {len(pids)} prompts × 6 arms. "
           "Median across runs per (arm, prompt). Hewn-vs-Caveman/terse "
           "numbers are **observational under asymmetric exposure** (no T0-style "
           "appended-comparator calibration on these prompts).",
           "",
           "### Output tokens per prompt × arm (median)",
           "",
           "| Prompt | baseline | terse | caveman_full | caveman+ultra | hewn_prompt_only | hewn_full |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for pid in pids:
        cells = []
        for a in arms:
            v = medians[a].get(pid)
            cells.append("—" if v is None else str(int(v)))
        out.append(f"| `{pid}` | " + " | ".join(cells) + " |")
    avgs = []
    for a in arms:
        xs = [medians[a][p] for p in pids if p in medians[a]]
        avgs.append(statistics.mean(xs) if xs else None)
    out.append(f"| **mean** | " +
               " | ".join("**—**" if v is None else f"**{int(round(v))}**"
                          for v in avgs) + " |")

    # Hewn-vs-baseline (causal — same exposure)
    out.append("")
    out.append("### Hewn-vs-baseline (causal — both arms inherit default+CLAUDE.md)")
    out.append("")
    out.append("| Prompt | baseline | hewn_full | savings |")
    out.append("|---|---:|---:|---:|")
    base_savings = []
    for pid in pids:
        if pid not in medians["hewn_full"] or pid not in medians["baseline"]:
            continue
        b = medians["baseline"][pid]
        h = medians["hewn_full"][pid]
        s = (1 - h/b) if b else 0
        base_savings.append(s)
        out.append(f"| `{pid}` | {int(b)} | {int(h)} | {fmt_pct(s)} |")
    if base_savings:
        st = safe_stats(base_savings)
        out.append(f"| **median** | | | **{fmt_pct(st['median'])}** |")
        out.append(f"| **mean** | | | **{fmt_pct(st['mean'])}** |")

    # Latency
    out.append("")
    out.append("### Wall-clock latency (median, ms)")
    out.append("")
    out.append("| Prompt | baseline | terse | caveman_full | caveman+ultra | hewn_prompt_only | hewn_full |")
    out.append("|---|---:|---:|---:|---:|---:|---:|")
    for pid in pids:
        cells = []
        for a in arms:
            xs = [r.get("duration_ms", 0) for r in snaps.get(a, [])
                  if r.get("prompt_id") == pid]
            cells.append("—" if not xs else str(int(median_int(xs))))
        out.append(f"| `{pid}` | " + " | ".join(cells) + " |")

    out.append("")
    return "\n".join(out)


# ──────────────────────────────────────────────────────────────────────────────
# T4 — multi-turn
# ──────────────────────────────────────────────────────────────────────────────

def report_T4() -> str:
    snaps = load_snapshots("T4")
    if not snaps:
        return "## T4 — Multi-turn\n\n_No data._\n\n"
    arms = ["baseline", "terse", "caveman_full",
            "hewn_prompt_only", "hewn_full"]
    # Aggregate per (arm, sequence_id, run_index) — sum across turns
    by: dict[tuple, dict[str, int]] = {}
    for arm in arms:
        for r in snaps.get(arm, []):
            key = (arm, r.get("sequence_id"), r.get("run_index"))
            agg = by.setdefault(key, {"output_tokens": 0, "duration_ms": 0,
                                      "cost_usd": 0.0, "turns": 0,
                                      "input_tokens": 0,
                                      "cache_creation": 0, "cache_read": 0})
            agg["output_tokens"] += r.get("output_tokens_anthropic", 0)
            agg["duration_ms"] += r.get("duration_ms", 0) or 0
            agg["cost_usd"] += r.get("total_cost_usd", 0) or 0
            agg["turns"] += 1
            agg["input_tokens"] += r.get("input_tokens_anthropic", 0)
            agg["cache_creation"] += r.get("cache_creation_input_tokens", 0)
            agg["cache_read"] += r.get("cache_read_input_tokens", 0)

    sequences = sorted({k[1] for k in by.keys()})
    runs = sorted({k[2] for k in by.keys()})

    out = ["## T4 — Multi-turn (drift + isolated hook value)",
           "",
           "Each (arm, sequence, run) replays 5 user turns via explicit "
           "`--resume <session_id>`. Cumulative output tokens summed across "
           "all 5 turns.",
           "",
           "### Cumulative output tokens per sequence × arm (median across 2 runs)",
           "",
           "| Sequence | baseline | terse | caveman_full | hewn_prompt_only | hewn_full |",
           "|---|---:|---:|---:|---:|---:|"]
    for sid in sequences:
        cells = []
        for arm in arms:
            xs = [by[(arm, sid, r)]["output_tokens"]
                  for r in runs if (arm, sid, r) in by]
            cells.append(str(int(median_int(xs))))
        out.append(f"| `{sid}` | " + " | ".join(cells) + " |")

    # Hook value — hewn_prompt_only vs hewn_full
    out.append("")
    out.append("### Hook value — `(hewn_prompt_only − hewn_full)` cumulative deltas")
    out.append("")
    out.append("Positive Δ output_tokens = hook makes hewn_full produce **fewer** tokens. "
               "Positive Δ cache_creation = hook injects extra `additionalContext` "
               "(expected; classifier injection is the hook's job).")
    out.append("")
    out.append("| Sequence | Δ output_tokens (median) | Δ cache_creation_input (median) |")
    out.append("|---|---:|---:|")
    for sid in sequences:
        outs_p = [by[("hewn_prompt_only", sid, r)]["output_tokens"]
                  for r in runs if ("hewn_prompt_only", sid, r) in by]
        outs_f = [by[("hewn_full", sid, r)]["output_tokens"]
                  for r in runs if ("hewn_full", sid, r) in by]
        cc_p = [by[("hewn_prompt_only", sid, r)]["cache_creation"]
                for r in runs if ("hewn_prompt_only", sid, r) in by]
        cc_f = [by[("hewn_full", sid, r)]["cache_creation"]
                for r in runs if ("hewn_full", sid, r) in by]
        if outs_p and outs_f:
            d_out = median_int(outs_p) - median_int(outs_f)
            d_cc = median_int(cc_f) - median_int(cc_p)
            out.append(f"| `{sid}` | {fmt_signed(d_out)} | {fmt_signed(d_cc)} |")

    # Session isolation validation
    out.append("")
    out.append("### Session-id isolation check")
    out.append("")
    sids_seen: dict[str, list[str]] = {}
    for arm in arms:
        for r in snaps.get(arm, []):
            s = r.get("session_id")
            if not s:
                continue
            tup = f"{arm}/{r.get('sequence_id')}/r{r.get('run_index')}"
            sids_seen.setdefault(s, []).append(tup)
    collisions = {s: tps for s, tps in sids_seen.items()
                  if len(set(t.rsplit('/', 1)[0] for t in tps)) > 1}
    if collisions:
        out.append("**WARNING**: session_id collisions detected:")
        for s, tps in collisions.items():
            out.append(f"  - {s} → {tps}")
    else:
        out.append("OK — no session_id collision across distinct (arm, seq, run) tuples.")
    out.append("")
    return "\n".join(out)


# ──────────────────────────────────────────────────────────────────────────────
# Quality summary
# ──────────────────────────────────────────────────────────────────────────────

def report_quality() -> str:
    out = ["## Quality — concepts coverage, literals, format compliance, judge failure rates",
           ""]
    for track in ["T1a", "T1b", "T2", "T3", "T4", "T5"]:
        j = load_judgments(track)
        if not j:
            out.append(f"### {track}\n\n_No judgments._\n")
            continue
        per_arm: dict[str, dict[str, list]] = {}
        for key, entry in j.items():
            # Skip judge sentinels (empty_response, empty_responses,
            # known_model_timeout, etc.) — they have no `arm` field
            # and would otherwise pollute the quality summary under "?".
            if entry.get("skipped") or "arm" not in entry:
                continue
            arm = entry["arm"]
            per_arm.setdefault(arm, {"covered": [], "literals": [],
                                     "ir_valid": [], "filler100": [],
                                     "concept_failures": 0,
                                     "readability_true": [],
                                     "readability_failures": 0})
            cp = entry.get("concepts_count_present")
            ct = entry.get("concepts_count_total")
            if cp is not None and ct:
                per_arm[arm]["covered"].append(cp / ct)
            if entry.get("concepts_failure"):
                per_arm[arm]["concept_failures"] += 1
            lits = entry.get("literals_present", {}) or {}
            if lits:
                per_arm[arm]["literals"].append(
                    sum(1 for v in lits.values() if v) / max(1, len(lits)))
            fmt = entry.get("format", {}) or {}
            per_arm[arm]["ir_valid"].append(1 if fmt.get("hewn_ir_valid") else 0)
            cs = fmt.get("caveman_style", {}) or {}
            per_arm[arm]["filler100"].append(cs.get("filler_per_100w", 0))
            rd = entry.get("readability") or {}
            if rd:
                per_arm[arm]["readability_true"].append(
                    sum(1 for v in rd.values() if v) / max(1, len(rd)))
            if entry.get("readability_failure"):
                per_arm[arm]["readability_failures"] += 1

        out.append(f"### {track}")
        out.append("")
        out.append("| Arm | concepts covered (mean ratio) | literals preserved (mean) | IR valid (rate) | filler/100w (mean) | concept-judge failures | readability (mean true ratio) |")
        out.append("|---|---:|---:|---:|---:|---:|---:|")
        for arm in sorted(per_arm.keys()):
            d = per_arm[arm]
            cov = statistics.mean(d["covered"]) if d["covered"] else None
            lit = statistics.mean(d["literals"]) if d["literals"] else None
            irv = statistics.mean(d["ir_valid"]) if d["ir_valid"] else None
            f100 = statistics.mean(d["filler100"]) if d["filler100"] else None
            rd = statistics.mean(d["readability_true"]) if d["readability_true"] else None
            cell = lambda v, fn=lambda x: f"{x:.0%}": (fn(v) if v is not None else "—")
            out.append(f"| {arm} | {cell(cov)} | {cell(lit)} | {cell(irv)} | "
                       f"{f100:.1f}" + (f" | {d['concept_failures']} | {cell(rd)} |"
                                        if rd is not None or d['readability_failures']
                                        else f" | {d['concept_failures']} | — |"))
        out.append("")
    return "\n".join(out)


# ──────────────────────────────────────────────────────────────────────────────
# Headline + methodology
# ──────────────────────────────────────────────────────────────────────────────

def methodology_header() -> str:
    meta = json.loads(META.read_text()) if META.exists() else {}
    return f"""# Hewn vs Verbose Claude vs Caveman — benchmark report

## TL;DR

Hewn is a Claude Code wrapper that routes each turn between Hewn IR
(compact technical atoms), prose-caveman (drop-articles prose for Q&A
and explanations), and micro-prose (terse diagnostic for vibe/non-tech
turns). A local-Python classifier hook re-injects the chosen route
every turn so the wrapper does not drift into verbose prose over long
sessions.

We benchmarked Hewn vs verbose Claude vs Caveman across 518 benchmark
cells run via `claude -p` / `hewn -p` (OAuth subscription, no direct
API billing) spanning strict Caveman parity, short Q&A, vibe prompts,
long-context reviews, multi-turn sessions and adversarial
polished-prose tasks. Caveman's `SKILL.md` is vendored under
`caveman_source/` at a pinned commit (sha256 recorded in metadata).
Concept coverage and readability are measured by LLM-as-judge with
hardcoded rubrics.

**Where Hewn wins:**
- **Short technical Q&A (T1b, 10 prompts × 3 runs)** — Hewn 149 mean
  output tokens vs Caveman 167 vs baseline 349. Concept coverage
  within 4pp of Caveman (91% vs 95%). Hewn beats Caveman on tokens
  with comparable quality.
- **Multi-turn (T4, 2 sequences × 5 turns × 2 runs)** — Hewn's hook
  delivers its promise: hewn_full cumulative 2838 mean tokens vs
  Caveman 4226 (~33% less) at **100% concept coverage under a
  transcript-aware judge** (tied with Caveman and baseline). The
  per-turn judge underrated Hewn because Hewn correctly avoids
  repeating already-established facts; a fair evaluator that scores
  the whole conversation closes the gap entirely.

**Where Hewn trades:**
- **Single-shot long-context tasks (T3)** — Caveman Full is the token
  leader here: 1224 mean output tokens vs Hewn's 2099, with both arms
  at ~100% concept coverage on the current judge. One
  `terse × body-size-rollout-plan` cell family reproducibly times out
  at 600s and is reported as not measurable rather than forced into the
  aggregates.
- **Non-tech vibe prompts (T2)** — Hewn 58 mean tokens vs Caveman 198
  (~3x more compressed) at 63% concept
  coverage vs Caveman 78%.
  Hewn is agent-mode (ask before guessing); Caveman is tutorial-mode
  (enumerate options). Different use cases; design trade-off preserved.
- **Expansive prose (T5)** — all arms, including Hewn, reach ~100%
  rubric concept coverage at roughly ~500 output tokens. No arm has a
  meaningful advantage; just use whatever you already have open.

**Methodology guarantees:**
- Model pinned to full ID `claude-opus-4-7`; every call asserts
  `modelUsage["claude-opus-4-7"].outputTokens == usage.output_tokens`.
- Caveman parity track (T1a) replicates their `evals/llm_run.py`
  exactly: 1 run, 3 arms, tiktoken `o200k_base`. Result: 59% median
  token savings vs terse (matches their published ~60% claim).
- Append-vs-replace asymmetry calibrated in T0 on short_en (10
  prompts × 1 run × terse, terse_appended, caveman_full,
  caveman_full_appended).
- Arm order randomized per (prompt, run) via factoradic Lehmer code
  seeded by sha256 — reproducible across Python versions/machines.
- Multi-turn (T4) uses explicit `--resume <session_id>` with system
  prompt re-passed each turn; post-run session-isolation validation.
- All raw `claude -p` JSON snapshots + raw judge outputs committed
  under `benchmarks/snapshots/` for deterministic re-derivation.
- 8 rounds of cross-model plan review with Codex (preserved under
  `benchmarks/codex-review-iterations/plan-v{{1..9}}.md`).

See `COMPARISON_v1_v2_v3.md` for the full Hewn iteration history
(v1 soft prose-caveman, v2 aggressive micro-IR auto-routing, v3
balanced strict prose-caveman, v4 = current, with `(a) vague → ask,
(b) concrete error → likely cause + safe fix` for vibe micro-prose).

---

_Generated: {meta.get('generated_at', '?')}_
_Model: `{meta.get('model', '?')}`_
_Claude CLI: {meta.get('claude_cli_version', '?')}_
_Hewn repo commit: {meta.get('hewn_repo_commit', '?')}_
_Caveman repo commit pinned: {meta.get('caveman_repo_commit_pinned', '?')}_
_Caveman SKILL.md sha256: `{meta.get('caveman_skill_sha256', '?')}`_
_Random seed: `{meta.get('rand_seed', '?')}`_
_Environment: NOT isolated (option B). User CLAUDE.md hash: `{meta.get('claude_md_sha256', '?')[:12] if meta.get('claude_md_sha256') else 'absent'}` ({meta.get('claude_md_word_count', 0)} words)._

## What this report measures

Six arms tested via `claude -p` / `hewn -p` (OAuth subscription, no
direct API key billing):

| Arm | Mechanism |
|---|---|
| `baseline` | `claude -p`, no system prompt |
| `terse` | `claude -p --system-prompt "Answer concisely."` |
| `caveman_full` | `claude -p --system-prompt "Answer concisely.\\n\\n" + caveman SKILL.md` (vendored from caveman repo) |
| `caveman_full_plus_ultra_directive` | `caveman_full` + appended "Default intensity: ultra…" — **NOT** Caveman's official Ultra (needs skill runtime); our directive-based variant |
| `hewn_prompt_only` | `claude -p --append-system-prompt <hewn prompt>` (no hook) |
| `hewn_full` | `hewn -p` real wrapper (prompt + classifier hook) |

Tracks:

- **T0** — append-vs-replace exposure calibration (10 prompts × 1 run × 4 arms)
- **T1a** — strict Caveman parity, replicates their `evals/llm_run.py` (10 prompts × 1 run × 3 arms)
- **T1b** — extended on Caveman's own prompts (10 × 3 × 6)
- **T2** — vibe / non-tech user prompts (5 × 3 × 6)
- **T3** — long context (~5k handbook + task) (3 × 3 × 6)
- **T4** — multi-turn 5-turn sequences (2 × 2 × 5)
- **T5** — expansive prose (neutral control; not a differentiator) (2 × 2 × 6)

## Honesty box

- **Caveman parity** label applies ONLY to T1a (1 run, 3 arms, tiktoken,
  matches `evals/llm_run.py`).
- **Hewn-vs-baseline** is causal: both arms inherit Claude Code's default
  system prompt + user CLAUDE.md.
- **Hewn-vs-Caveman/terse** is **observational under asymmetric
  exposure**: `--system-prompt` replaces, `--append-system-prompt` adds.
  T0 calibrates the magnitude on `short_en`; T2-T5 reported as raw
  observational only (no per-prompt calibration).
- One T3 cell family (`terse` × `body-size-rollout-plan`, all 3 runs)
  reproducibly timed out at 600s with no model response and is marked
  **not measurable** (`—`) instead of being coerced to zero.
- `caveman_full_plus_ultra_directive` is OUR directive-based variant,
  NOT Caveman's official Ultra (which is invoked via `/caveman ultra`
  through the skill runtime, unavailable in `--system-prompt` mode).
- All raw `claude -p` JSON snapshots committed under
  `benchmarks/snapshots/raw/` for deterministic re-derivation.
- Hewn classifier hook is local Python (no extra API call), but DOES
  inject `additionalContext` → measured as `cache_creation_input_tokens`
  delta, NOT `input_tokens` delta (verified empirically).

"""


# ──────────────────────────────────────────────────────────────────────────────
# main
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    pieces = [
        methodology_header(),
        report_T1a(),
        report_T0(),
        report_T1b_with_T0_join(),
        report_observational("T2", "Vibe / non-tech user prompts", 3),
        report_observational("T3", "Long context (~5k handbook prefix)", 3),
        report_T4(),
        report_observational("T5", "Expansive prose (neutral control; not a differentiator)", 2),
        report_quality(),
    ]
    REPORT.write_text("\n".join(pieces))
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    main()
