#!/usr/bin/env python3
"""Side-by-side comparison of Hewn v1 (original 2026-04-22 run) vs v2
(post-Codex prompt+hook tightening) for the Hewn arms only.

Reads v1 snapshots from <arm>_v1/ and v2 snapshots from <arm>/ in each
track. Caveman/baseline/terse arms are unchanged across versions, so we
compare them too as a sanity check (should be near-identical modulo
model temperature).

Writes report/COMPARISON_v1_v2.md.
"""
from __future__ import annotations
import json
import statistics
from pathlib import Path

BENCH = Path(__file__).resolve().parent
RAW = BENCH / "snapshots" / "raw"
OUT = BENCH / "report" / "COMPARISON_v1_v2.md"


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
        arr.append(d.get(key, 0))
    return statistics.median(arr) if arr else 0


def cumulative_seq(track: str, arm: str, seq_id: str,
                   key: str = "output_tokens_anthropic") -> list[int]:
    """Sum across turns per (run); return list of per-run cumulatives."""
    arm_dir = RAW / track / arm
    if not arm_dir.exists():
        return []
    by_run: dict[int, int] = {}
    for p in sorted(arm_dir.glob(f"{seq_id}_r*_t*.json")):
        d = json.loads(p.read_text())
        run = d.get("run_index", 0)
        by_run[run] = by_run.get(run, 0) + d.get(key, 0)
    return list(by_run.values())


def fmt_signed(x: float) -> str:
    return f"{int(x):+d}" if abs(x) >= 1 else f"{x:+.2f}"


def fmt_pct(num: float, den: float) -> str:
    if not den:
        return "—"
    pct = (num - den) / den * 100
    sign = "+" if pct >= 0 else "−"
    return f"{sign}{abs(pct):.0f}%"


def comparison_table(track: str, prompts: list[str], comparators: list[str]) -> str:
    out = [f"## {track} — hewn_full v1 → v2 vs unchanged comparators",
           "",
           f"| prompt | hewn_full v1 | hewn_full v2 | Δ tokens | Δ % | "
           + " | ".join(f"{c} (unchanged)" for c in comparators) + " |",
           "|" + "---|" * (4 + len(comparators)) + "---|"]
    v1_vals, v2_vals = [], []
    cmp_vals = {c: [] for c in comparators}
    for pid in prompts:
        v1 = median_of_arm(track, "hewn_full_v1", pid)
        v2 = median_of_arm(track, "hewn_full", pid)
        v1_vals.append(v1)
        v2_vals.append(v2)
        cmp_cells = []
        for c in comparators:
            v = median_of_arm(track, c, pid)
            cmp_vals[c].append(v)
            cmp_cells.append(str(int(v)))
        out.append(f"| `{pid}` | {int(v1)} | {int(v2)} | "
                   f"{fmt_signed(v2 - v1)} | {fmt_pct(v2, v1)} | "
                   + " | ".join(cmp_cells) + " |")
    if v1_vals:
        out.append(f"| **mean** | **{int(statistics.mean(v1_vals))}** | "
                   f"**{int(statistics.mean(v2_vals))}** | "
                   f"**{fmt_signed(statistics.mean(v2_vals) - statistics.mean(v1_vals))}** | "
                   f"**{fmt_pct(statistics.mean(v2_vals), statistics.mean(v1_vals))}** | "
                   + " | ".join(f"**{int(statistics.mean(cmp_vals[c]))}**"
                                for c in comparators) + " |")
    out.append("")
    return "\n".join(out)


def quality_compare(track: str) -> str:
    j = json.loads((BENCH / "snapshots" / f"judgments_{track}.json").read_text())
    rows = {"hewn_full_v1": [], "hewn_full": [],
            "caveman_full": [], "caveman_full_plus_ultra_directive": [],
            "baseline": [], "terse": []}
    for k, v in j.items():
        arm = v.get("arm", "?")
        if arm not in rows:
            continue
        cp = v.get("concepts_count_present"); ct = v.get("concepts_count_total")
        if cp is not None and ct:
            rows[arm].append(cp / ct)
    out = [f"### {track} concept coverage (mean ratio)", ""]
    out.append("| arm | mean coverage | n |")
    out.append("|---|---:|---:|")
    for arm in ["baseline", "terse", "caveman_full",
                "caveman_full_plus_ultra_directive",
                "hewn_full_v1", "hewn_full"]:
        xs = rows.get(arm, [])
        if not xs:
            out.append(f"| {arm} | — | 0 |")
        else:
            out.append(f"| {arm} | {statistics.mean(xs):.0%} | {len(xs)} |")
    out.append("")
    return "\n".join(out)


def t4_compare() -> str:
    out = ["## T4 — multi-turn cumulative tokens v1 → v2", ""]
    out.append("| sequence | hewn_full v1 (median) | hewn_full v2 (median) | "
               "Δ tokens | Δ % | caveman_full | baseline |")
    out.append("|---|---:|---:|---:|---:|---:|---:|")
    for sid in ["debug-prod-incident", "design-feature"]:
        v1 = cumulative_seq("T4", "hewn_full_v1", sid)
        v2 = cumulative_seq("T4", "hewn_full", sid)
        cv = cumulative_seq("T4", "caveman_full", sid)
        bl = cumulative_seq("T4", "baseline", sid)
        v1m = statistics.median(v1) if v1 else 0
        v2m = statistics.median(v2) if v2 else 0
        cvm = statistics.median(cv) if cv else 0
        blm = statistics.median(bl) if bl else 0
        out.append(f"| `{sid}` | {int(v1m)} | {int(v2m)} | "
                   f"{fmt_signed(v2m - v1m)} | {fmt_pct(v2m, v1m)} | "
                   f"{int(cvm)} | {int(blm)} |")
    out.append("")
    return "\n".join(out)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    parts = ["# Hewn v1 → v2 comparison",
             "",
             "v1 = original 2026-04-22 run with the soft prose-caveman directive.",
             "v2 = post-Codex tightening: stricter prose-caveman + new "
             "MICRO_PROSE mode + expanded IR routing for technical Q&A "
             "(see commit after `66c9d8d`).",
             "",
             "Caveman/baseline/terse arms are UNCHANGED across versions and "
             "shown as reference. Differences in those columns reflect model "
             "nondeterminism only.",
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
    cmp_arms = ["caveman_full", "caveman_full_plus_ultra_directive", "baseline"]
    parts.append(comparison_table("T1b", short_en, cmp_arms))
    parts.append(comparison_table("T2", vibe_en, cmp_arms))
    parts.append(comparison_table("T3", long_en, cmp_arms))
    parts.append(comparison_table("T5", expansive_en, cmp_arms))
    parts.append(t4_compare())
    parts.append("## Quality side-by-side")
    parts.append("")
    for track in ["T1b", "T2", "T3", "T5", "T4"]:
        parts.append(quality_compare(track))
    OUT.write_text("\n".join(parts))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
