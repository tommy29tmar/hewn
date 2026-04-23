#!/usr/bin/env python3
"""Three-way comparison: Hewn v1 vs v2 vs v3 + Caveman/baseline reference.

v1 = original 2026-04-22 — soft prose-caveman directive
v2 = post-Codex tightening — micro-IR for Q&A; tokens crashed but quality regressed
v3 = post-rollback — strict prose-caveman without auto-IR; balance attempt

Reads <arm>_v1/, <arm>_v2/, <arm>/ (current = v3) for hewn arms.
Other arms are unchanged across versions.
"""
from __future__ import annotations
import json
import statistics
from pathlib import Path

BENCH = Path(__file__).resolve().parent
RAW = BENCH / "snapshots" / "raw"
OUT = BENCH / "report" / "COMPARISON_v1_v2_v3.md"


def median_of_arm(track: str, arm: str, prompt_id: str,
                  key: str = "output_tokens_anthropic") -> float:
    arr = []
    arm_dir = RAW / track / arm
    if not arm_dir.exists():
        return 0
    for p in sorted(arm_dir.glob(f"{prompt_id}_r*.json")):
        if "_t" in p.stem:
            continue
        d = json.loads(p.read_text())
        if d.get("skipped") or d.get("error"):
            continue
        arr.append(d.get(key, 0))
    return statistics.median(arr) if arr else 0


def cumulative_seq(track: str, arm: str, seq_id: str,
                   key: str = "output_tokens_anthropic") -> list[int]:
    arm_dir = RAW / track / arm
    if not arm_dir.exists():
        return []
    by_run: dict[int, int] = {}
    for p in sorted(arm_dir.glob(f"{seq_id}_r*_t*.json")):
        d = json.loads(p.read_text())
        if d.get("skipped") or d.get("error"):
            continue
        run = d.get("run_index", 0)
        by_run[run] = by_run.get(run, 0) + d.get(key, 0)
    return list(by_run.values())


def fmt_signed(x: float) -> str:
    return f"{int(x):+d}" if abs(x) >= 1 else f"{x:+.2f}"


def comparison_table(track: str, prompts: list[str]) -> str:
    out = [f"## {track} — hewn_full v1 → v2 → v3 vs comparators",
           "",
           "| prompt | v1 | v2 | v3 | caveman_full | caveman+ultra | baseline |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    series = {"v1": [], "v2": [], "v3": [], "cav": [], "cav_u": [], "base": []}
    for pid in prompts:
        v1 = median_of_arm(track, "hewn_full_v1", pid)
        v2 = median_of_arm(track, "hewn_full_v2", pid)
        v3 = median_of_arm(track, "hewn_full", pid)
        cv = median_of_arm(track, "caveman_full", pid)
        cu = median_of_arm(track, "caveman_full_plus_ultra_directive", pid)
        bl = median_of_arm(track, "baseline", pid)
        series["v1"].append(v1); series["v2"].append(v2); series["v3"].append(v3)
        series["cav"].append(cv); series["cav_u"].append(cu); series["base"].append(bl)
        out.append(f"| `{pid}` | {int(v1)} | {int(v2)} | {int(v3)} | "
                   f"{int(cv)} | {int(cu)} | {int(bl)} |")
    if series["v1"]:
        means = {k: statistics.mean(v) for k, v in series.items()}
        out.append(f"| **mean** | **{int(means['v1'])}** | "
                   f"**{int(means['v2'])}** | **{int(means['v3'])}** | "
                   f"**{int(means['cav'])}** | **{int(means['cav_u'])}** | "
                   f"**{int(means['base'])}** |")
    out.append("")
    return "\n".join(out)


def quality_compare_t4_transcript() -> str:
    p = BENCH / "snapshots" / "judgments_T4_transcript.json"
    if not p.exists():
        return ""
    j = json.loads(p.read_text())
    arms_order = ["baseline", "terse", "caveman_full",
                  "hewn_full_v1", "hewn_full_v2", "hewn_full"]
    rows: dict[str, list[float]] = {a: [] for a in arms_order}
    for k, v in j.items():
        arm = v.get("arm", "?")
        if arm not in rows:
            continue
        cp = v.get("concepts_count_present"); ct = v.get("concepts_count_total")
        if cp is not None and ct:
            rows[arm].append(cp / ct)
    out = ["### T4 transcript-aware concept coverage",
           "",
           "Fairer evaluator for multi-turn: judges the FULL conversation "
           "not each turn in isolation, so the assistant is not penalized "
           "for NOT restating concepts it already established.",
           "",
           "| arm | transcript coverage | n |",
           "|---|---:|---:|"]
    for arm in arms_order:
        xs = rows.get(arm, [])
        if not xs:
            out.append(f"| {arm} | — | 0 |")
        else:
            out.append(f"| {arm} | {statistics.mean(xs):.0%} | {len(xs)} |")
    out.append("")
    return "\n".join(out)


def quality_compare(track: str) -> str:
    j = json.loads((BENCH / "snapshots" / f"judgments_{track}.json").read_text())
    arms_order = ["baseline", "terse", "caveman_full",
                  "caveman_full_plus_ultra_directive",
                  "hewn_full_v1", "hewn_full_v2", "hewn_full"]
    rows = {a: [] for a in arms_order}
    for k, v in j.items():
        arm = v.get("arm", "?")
        if arm not in rows:
            continue
        cp = v.get("concepts_count_present"); ct = v.get("concepts_count_total")
        if cp is not None and ct:
            rows[arm].append(cp / ct)
    out = [f"### {track} concept coverage (mean ratio)", "",
           "| arm | mean coverage | n |", "|---|---:|---:|"]
    for arm in arms_order:
        xs = rows.get(arm, [])
        if not xs:
            out.append(f"| {arm} | — | 0 |")
        else:
            out.append(f"| {arm} | {statistics.mean(xs):.0%} | {len(xs)} |")
    out.append("")
    return "\n".join(out)


def t4_compare() -> str:
    out = ["## T4 — multi-turn cumulative tokens v1 → v2 → v3", ""]
    out.append("| sequence | v1 | v2 | v3 | caveman_full | baseline |")
    out.append("|---|---:|---:|---:|---:|---:|")
    for sid in ["debug-prod-incident", "design-feature"]:
        v1 = cumulative_seq("T4", "hewn_full_v1", sid)
        v2 = cumulative_seq("T4", "hewn_full_v2", sid)
        v3 = cumulative_seq("T4", "hewn_full", sid)
        cv = cumulative_seq("T4", "caveman_full", sid)
        bl = cumulative_seq("T4", "baseline", sid)
        v1m = statistics.median(v1) if v1 else 0
        v2m = statistics.median(v2) if v2 else 0
        v3m = statistics.median(v3) if v3 else 0
        cvm = statistics.median(cv) if cv else 0
        blm = statistics.median(bl) if bl else 0
        out.append(f"| `{sid}` | {int(v1m)} | {int(v2m)} | {int(v3m)} | "
                   f"{int(cvm)} | {int(blm)} |")
    out.append("")
    return "\n".join(out)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    parts = ["# Hewn v1 → v2 → v3 comparison",
             "",
             "v1 = original (soft prose-caveman directive)",
             "v2 = Codex first attempt (micro-IR auto-routing for Q&A → "
             "huge token cuts but concept coverage crashed)",
             "v3 = balance attempt (strict prose-caveman, no auto-IR for "
             "Q&A, micro-prose only for vibe/non-tech)",
             "",
             "Caveman/baseline/terse arms unchanged — shown for reference.",
             ""]
    short_en = ["cors-errors","debounce-search","explain-db-pool",
                "fix-node-memory-leak","git-rebase-vs-merge",
                "hash-table-collisions","queue-vs-topic",
                "react-rerender-parent","sql-explain","tcp-vs-udp"]
    vibe_en = ["add-search-bar","login-button-broken","make-website-faster",
               "spaghetti-code","typeerror-undefined-map"]
    long_en = ["body-size-rollout-plan","rate-limit-xff-review",
               "transfer-handler-review"]
    expansive_en = ["smart-drafts-release-note","outage-apology-email"]
    parts.append(comparison_table("T1b", short_en))
    parts.append(comparison_table("T2", vibe_en))
    parts.append(comparison_table("T3", long_en))
    parts.append(comparison_table("T5", expansive_en))
    parts.append(t4_compare())
    parts.append("## Quality side-by-side")
    parts.append("")
    for track in ["T1b", "T2", "T3", "T5", "T4"]:
        parts.append(quality_compare(track))
    parts.append(quality_compare_t4_transcript())
    OUT.write_text("\n".join(parts))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
