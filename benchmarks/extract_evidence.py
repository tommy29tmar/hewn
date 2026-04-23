#!/usr/bin/env python3
"""Extract 6-8 side-by-side full-text examples for report/evidence/.

Picks representative cases:
- 2 from T1a (Caveman parity headline)
- 2 from T1b (extended with hewn_full)
- 1 from T2 (vibe / non-tech)
- 1 from T3 (long context — honesty case where Caveman wins single-shot)
- 1 from T4 (multi-turn — sequence summary)
- 1 from T5 (expansive — neutral control, not a differentiator)

Each evidence file contains: original prompt, every arm's full response
(token count + median latency), so a reader can verify every claim.
"""
from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

BENCH = Path(__file__).resolve().parent
RAW = BENCH / "snapshots" / "raw"
OUT = BENCH / "report" / "evidence"


def load_runs(track: str, arm: str, prompt_id: str) -> list[dict]:
    path = RAW / track / arm
    if not path.exists():
        return []
    out = []
    for p in sorted(path.glob(f"{prompt_id}_r*.json")):
        if "_t" in p.stem:
            continue
        rec = json.loads(p.read_text())
        if rec.get("skipped") or rec.get("error"):
            continue
        out.append(rec)
    return out


def median_run(runs: list[dict]) -> dict | None:
    if not runs:
        return None
    runs = sorted(runs, key=lambda r: r.get("output_tokens_anthropic", 0))
    return runs[len(runs) // 2]


def emit_single(track: str, arms: list[str], prompt_id: str,
                prompt_text: str, out_path: Path) -> None:
    lines = [f"# Evidence — {track} / `{prompt_id}`",
             "",
             "## Prompt",
             "",
             "```text",
             prompt_text.strip(),
             "```",
             ""]
    for arm in arms:
        runs = load_runs(track, arm, prompt_id)
        med = median_run(runs)
        if med is None:
            continue
        lat_med = (statistics.median(
            [r.get("duration_ms", 0) for r in runs])
            if runs else 0)
        lines.append(f"## `{arm}`")
        lines.append("")
        lines.append(
            f"output_tokens (anthropic) = **{med.get('output_tokens_anthropic')}**, "
            f"output_tokens (tiktoken) = {med.get('output_tokens_tiktoken')}, "
            f"input_tokens = {med.get('input_tokens_anthropic')}, "
            f"cache_creation = {med.get('cache_creation_input_tokens')}, "
            f"cache_read = {med.get('cache_read_input_tokens')}, "
            f"latency wall = {int(med.get('duration_ms', 0))}ms "
            f"(median across runs: {int(lat_med)}ms)")
        lines.append("")
        lines.append("```text")
        lines.append((med.get("result") or "").strip())
        lines.append("```")
        lines.append("")
    OUT.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines))
    print(f"Wrote {out_path}")


def emit_multiturn(seq_id: str, arms: list[str], turns: list[str],
                   out_path: Path) -> None:
    lines = [f"# Evidence — T4 / `{seq_id}` (5-turn cumulative)",
             ""]
    # Pick run 1
    for arm in arms:
        arm_dir = RAW / "T4" / arm
        if not arm_dir.exists():
            continue
        per_turn = []
        for t, user_msg in enumerate(turns, start=1):
            p = arm_dir / f"{seq_id}_r1_t{t}.json"
            if not p.exists():
                per_turn.append(None)
                continue
            per_turn.append(json.loads(p.read_text()))
        if not any(per_turn):
            continue
        cum_out = sum((r or {}).get("output_tokens_anthropic", 0)
                      for r in per_turn)
        cum_dur = sum((r or {}).get("duration_ms", 0)
                      for r in per_turn)
        lines.append(f"## `{arm}` — cumulative output_tokens={cum_out}, "
                     f"cumulative wall={int(cum_dur)}ms")
        lines.append("")
        for t, (user_msg, rec) in enumerate(zip(turns, per_turn), start=1):
            lines.append(f"### Turn {t}")
            lines.append("")
            lines.append("**user:**")
            lines.append("")
            lines.append("```text")
            lines.append(user_msg)
            lines.append("```")
            lines.append("")
            lines.append("**assistant:**")
            lines.append("")
            if rec is None:
                lines.append("_(no snapshot)_")
            else:
                lines.append(
                    f"_output_tokens={rec.get('output_tokens_anthropic')}_")
                lines.append("")
                lines.append("```text")
                lines.append((rec.get("result") or "").strip())
                lines.append("```")
            lines.append("")
        lines.append("---")
        lines.append("")
    OUT.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines))
    print(f"Wrote {out_path}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # T1a — pick 2 representative
    arms_t1a = ["baseline", "terse", "caveman_full"]
    emit_single("T1a", arms_t1a, "react-rerender-parent",
                "Why does my React component re-render every time the "
                "parent updates?",
                OUT / "01_T1a_react_rerender.md")
    emit_single("T1a", arms_t1a, "explain-db-pool",
                "Explain database connection pooling.",
                OUT / "02_T1a_db_pool.md")

    # T1b — pick 2 with hewn arms
    arms_full = ["baseline", "terse", "caveman_full",
                 "caveman_full_plus_ultra_directive",
                 "hewn_prompt_only", "hewn_full"]
    emit_single("T1b", arms_full, "tcp-vs-udp",
                "What's the difference between TCP and UDP?",
                OUT / "03_T1b_tcp_vs_udp.md")
    emit_single("T1b", arms_full, "git-rebase-vs-merge",
                "How does git rebase differ from git merge?",
                OUT / "04_T1b_rebase_vs_merge.md")

    # T2 — vibe
    emit_single("T2", arms_full, "login-button-broken",
                "the login button doesnt work people are complaining help",
                OUT / "05_T2_login_broken.md")

    # T3 — long context (honesty: Caveman wins single-shot)
    handbook = (BENCH / "prompts" / "long_handbook.txt").read_text()
    raw = (BENCH / "prompts" / "long_en.txt").read_text()
    body = [p.strip() for p in raw.split("---PROMPT---") if p.strip()
            and not p.lstrip().startswith("#")][0]
    emit_single("T3", arms_full, "rate-limit-xff-review",
                f"[handbook ~{len(handbook)//4} tokens prefixed]\n\n[Task]\n{body}",
                OUT / "06_T3_xff_review.md")

    # T4 — multi-turn
    seqs = json.loads(
        (BENCH / "prompts" / "multiturn_en.json").read_text())["sequences"]
    seq = next(s for s in seqs if s["id"] == "debug-prod-incident")
    arms_t4 = ["baseline", "terse", "caveman_full",
               "hewn_prompt_only", "hewn_full"]
    emit_multiturn(seq["id"], arms_t4, seq["turns"],
                   OUT / "07_T4_debug_prod_incident.md")

    # T5 — expansive (neutral control)
    raw = (BENCH / "prompts" / "expansive_en.txt").read_text()
    blocks = [p.strip() for p in raw.split("---PROMPT---") if p.strip()
              and not p.lstrip().startswith("#")]
    emit_single("T5", arms_full, "smart-drafts-release-note",
                blocks[0],
                OUT / "08_T5_smart_drafts_release_note.md")


if __name__ == "__main__":
    main()
