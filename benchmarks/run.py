#!/usr/bin/env python3
"""Hewn benchmark runner — invokes claude -p / hewn -p per (track, prompt, arm, run).

Captures full --output-format json payload + tiktoken o200k_base output token count.
Idempotent: skips a call if its snapshot file already exists.
Supports T0 (calibration), T1a (Caveman parity), T1b/T2/T3/T5 (single-turn), T4 (multi-turn).

Usage:
  uv run --with tiktoken benchmarks/run.py --track T1a
  uv run --with tiktoken benchmarks/run.py --track all
  uv run --with tiktoken benchmarks/run.py --smoke

Requires:
  - `claude` CLI on PATH, authenticated (OAuth/Max subscription)
  - `bash <REPO>/integrations/claude-code/bin/hewn` invokable
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import tiktoken

REPO = Path(__file__).resolve().parent.parent
BENCH = Path(__file__).resolve().parent
HEWN_BIN = REPO / "integrations" / "claude-code" / "bin" / "hewn"
ARMS = BENCH / "arms"
PROMPTS = BENCH / "prompts"
SNAPSHOTS = BENCH / "snapshots"
RAW = SNAPSHOTS / "raw"
META = SNAPSHOTS / "metadata.json"
RAND_SEED = "hewn-bench-v1"
MODEL = "claude-opus-4-7"

ENCODING = tiktoken.get_encoding("o200k_base")


# ──────────────────────────────────────────────────────────────────────────────
# permutation — factoradic Lehmer code, version-independent
# ──────────────────────────────────────────────────────────────────────────────

def factoradic_permutation(arms: list, digest_int: int) -> list:
    remaining = list(arms)
    result = []
    for i in range(len(remaining), 0, -1):
        idx = digest_int % i
        digest_int //= i
        result.append(remaining.pop(idx))
    return result


def perm_for(prompt_id: str, run_index: int, arms: list) -> list:
    if len(arms) <= 1:
        return list(arms)
    key = f"{RAND_SEED}:{prompt_id}:{run_index}"
    digest = hashlib.sha256(key.encode()).hexdigest()
    return factoradic_permutation(arms, int(digest, 16))


def digest_for(prompt_id: str, run_index: int) -> str:
    return hashlib.sha256(f"{RAND_SEED}:{prompt_id}:{run_index}".encode()).hexdigest()


# ──────────────────────────────────────────────────────────────────────────────
# subprocess invocation
# ──────────────────────────────────────────────────────────────────────────────

def arm_content(arm: str) -> str:
    p = ARMS / f"{arm}.txt"
    return p.read_text() if p.exists() else ""


def build_cmd(arm: str, prompt: str, resume: str | None = None) -> list[str]:
    """Build the subprocess argv for a given arm.

    Mechanism per arm — see plan v9:
      - baseline:                            claude -p --model X
      - terse, caveman_full, ..._directive:  claude -p --model X --system-prompt <content>
      - terse_appended, caveman_full_appended, hewn_prompt_only:
                                             claude -p --model X --append-system-prompt <content>
      - hewn_full:                           hewn -p --model X --output-format json
    """
    if arm == "hewn_full":
        cmd = ["bash", str(HEWN_BIN), "-p", "--model", MODEL,
               "--output-format", "json"]
    else:
        cmd = ["claude", "-p", "--model", MODEL, "--output-format", "json"]
        if arm in ("terse", "caveman_full", "caveman_full_plus_ultra_directive"):
            cmd += ["--system-prompt", arm_content(arm)]
        elif arm in ("terse_appended", "caveman_full_appended", "hewn_prompt_only"):
            cmd += ["--append-system-prompt", arm_content(arm)]
        elif arm == "baseline":
            pass
        else:
            raise ValueError(f"unknown arm: {arm}")

    if resume:
        cmd += ["--resume", resume]
    cmd.append(prompt)
    return cmd


def call_once(arm: str, prompt: str, resume: str | None = None,
              max_retries: int = 3) -> dict[str, Any]:
    """Invoke claude -p / hewn -p, capture --output-format json."""
    cmd = build_cmd(arm, prompt, resume)
    delays = [10.0, 30.0, 90.0]
    for attempt in range(max_retries + 1):
        t0 = time.monotonic()
        proc = subprocess.run(cmd, capture_output=True, text=True)
        elapsed_ms = (time.monotonic() - t0) * 1000
        if proc.returncode != 0:
            err = (proc.stderr or "")[:500]
            if attempt < max_retries:
                d = delays[min(attempt, len(delays) - 1)]
                print(f"  [retry {attempt+1}] arm={arm} rc={proc.returncode} "
                      f"err={err!r} sleep={d}s", file=sys.stderr)
                time.sleep(d)
                continue
            raise RuntimeError(f"call failed after {max_retries} retries: {err!r}")
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            err = proc.stdout[:500]
            if attempt < max_retries:
                d = delays[min(attempt, len(delays) - 1)]
                print(f"  [retry {attempt+1}] arm={arm} bad JSON: {e} "
                      f"out={err!r} sleep={d}s", file=sys.stderr)
                time.sleep(d)
                continue
            raise RuntimeError(f"bad JSON: {e}: {err!r}")
        return _enrich(payload, elapsed_ms, arm)
    raise RuntimeError("unreachable")


def _enrich(payload: dict, wallclock_ms: float, arm: str) -> dict[str, Any]:
    """Add tiktoken count + cache-state + wrapper-overhead derived metrics."""
    text = payload.get("result", "") or ""
    usage = payload.get("usage", {}) or {}
    out_anth = usage.get("output_tokens", 0)
    in_anth = usage.get("input_tokens", 0)
    cc = usage.get("cache_creation_input_tokens", 0)
    cr = usage.get("cache_read_input_tokens", 0)
    duration_api = payload.get("duration_api_ms", 0)

    derived = {
        "output_tokens_tiktoken": len(ENCODING.encode(text)),
        "output_tokens_anthropic": out_anth,
        "input_tokens_anthropic": in_anth,
        "cache_creation_input_tokens": cc,
        "cache_read_input_tokens": cr,
        "total_input_tokens": in_anth + cc + cr,
        "cache_state": "warm" if cr > 0 else "cold",
        "wallclock_ms": wallclock_ms,
        "duration_ms": payload.get("duration_ms", 0),
        "duration_api_ms": duration_api,
        "wrapper_overhead_ms": (
            wallclock_ms - duration_api if arm == "hewn_full" else None
        ),
        "stop_reason": payload.get("stop_reason"),
        "num_turns": payload.get("num_turns"),
        "session_id": payload.get("session_id"),
        "total_cost_usd": payload.get("total_cost_usd"),
        "model_used": _detect_model(payload),
        "result": text,
    }

    # Model assertion: opus output tokens in modelUsage must equal usage.output_tokens.
    mu = (payload.get("modelUsage") or {}).get(MODEL) or {}
    derived["assertion_pass"] = mu.get("outputTokens") == out_anth

    derived["raw_payload"] = payload
    return derived


def _detect_model(payload: dict) -> str:
    mu = payload.get("modelUsage") or {}
    return ",".join(sorted(mu.keys()))


# ──────────────────────────────────────────────────────────────────────────────
# snapshot persistence
# ──────────────────────────────────────────────────────────────────────────────

def snapshot_path(track: str, arm: str, prompt_id: str, run_index: int,
                  turn: int | None = None) -> Path:
    suffix = f"_t{turn}" if turn is not None else ""
    return RAW / track / arm / f"{prompt_id}_r{run_index}{suffix}.json"


def write_snapshot(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2))


def already_done(path: Path) -> bool:
    return path.exists()


# ──────────────────────────────────────────────────────────────────────────────
# track configuration
# ──────────────────────────────────────────────────────────────────────────────

T0_ARMS = ["terse", "terse_appended", "caveman_full", "caveman_full_appended"]
T1A_ARMS = ["baseline", "terse", "caveman_full"]
EXTENDED_ARMS = [
    "baseline", "terse", "caveman_full",
    "caveman_full_plus_ultra_directive",
    "hewn_prompt_only", "hewn_full",
]
T4_ARMS = ["baseline", "terse", "caveman_full",
           "hewn_prompt_only", "hewn_full"]


def load_short_en() -> list[tuple[str, str]]:
    lines = (PROMPTS / "short_en.txt").read_text().splitlines()
    items = [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]
    # ids match Caveman benchmarks/prompts.json conventions
    ids = [
        "react-rerender-parent", "explain-db-pool", "tcp-vs-udp",
        "fix-node-memory-leak", "sql-explain", "hash-table-collisions",
        "cors-errors", "debounce-search", "git-rebase-vs-merge",
        "queue-vs-topic",
    ]
    return list(zip(ids, items))


def load_vibe_en() -> list[tuple[str, str]]:
    lines = (PROMPTS / "vibe_en.txt").read_text().splitlines()
    items = [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]
    ids = [
        "make-website-faster", "login-button-broken", "add-search-bar",
        "typeerror-undefined-map", "spaghetti-code",
    ]
    return list(zip(ids, items))


def load_blocks(filename: str, ids: list[str]) -> list[tuple[str, str]]:
    """Read prompts file split by `---PROMPT---` separator lines."""
    raw = (PROMPTS / filename).read_text()
    parts = [p.strip() for p in raw.split("---PROMPT---") if p.strip()
             and not p.lstrip().startswith("#")]
    # the leading comment block also gets returned by split if not preceded by separator;
    # filter blocks that look like all-comment headers
    parts = [p for p in parts
             if not all(line.startswith("#") or not line.strip()
                        for line in p.splitlines())]
    return list(zip(ids, parts))


def load_long_en() -> list[tuple[str, str]]:
    handbook = (PROMPTS / "long_handbook.txt").read_text()
    blocks = load_blocks("long_en.txt",
                         ["rate-limit-xff-review",
                          "transfer-handler-review",
                          "body-size-rollout-plan"])
    return [(pid, f"{handbook}\n\n[Task]\n{body}") for pid, body in blocks]


def load_expansive_en() -> list[tuple[str, str]]:
    return load_blocks("expansive_en.txt",
                       ["smart-drafts-release-note",
                        "outage-apology-email"])


def load_multiturn() -> list[dict]:
    return json.loads((PROMPTS / "multiturn_en.json").read_text())["sequences"]


# ──────────────────────────────────────────────────────────────────────────────
# track runners
# ──────────────────────────────────────────────────────────────────────────────

def run_single_turn_track(track: str, arms: list[str],
                          prompts: list[tuple[str, str]],
                          n_runs: int, randomize: bool = True) -> None:
    print(f"\n=== {track} | {len(prompts)} prompts × {n_runs} runs × "
          f"{len(arms)} arms = {len(prompts)*n_runs*len(arms)} calls ===",
          flush=True)
    for run_index in range(1, n_runs + 1):
        for prompt_id, prompt in prompts:
            ordered = (perm_for(prompt_id, run_index, arms) if randomize
                       else list(arms))
            for arm_order_idx, arm in enumerate(ordered):
                path = snapshot_path(track, arm, prompt_id, run_index)
                if already_done(path):
                    continue
                rec_meta = {
                    "track": track, "arm": arm, "prompt_id": prompt_id,
                    "run_index": run_index,
                    "arm_order_index": arm_order_idx,
                    "arm_order_full": ordered,
                    "digest_hex": digest_for(prompt_id, run_index),
                    "seed": RAND_SEED,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                print(f"  [{track}] {prompt_id} | r{run_index} | {arm} "
                      f"(pos {arm_order_idx}/{len(ordered)})", flush=True)
                try:
                    rec = call_once(arm, prompt)
                except Exception as e:
                    print(f"    ERROR: {e}", file=sys.stderr)
                    rec = {"error": str(e)}
                write_snapshot(path, {**rec_meta, **rec})


def run_multiturn_track(track: str, arms: list[str], n_runs: int) -> None:
    sequences = load_multiturn()
    total = sum(len(s["turns"]) for s in sequences) * n_runs * len(arms)
    print(f"\n=== {track} | {len(sequences)} sequences × {n_runs} runs × "
          f"{len(arms)} arms = {total} calls ===", flush=True)
    for run_index in range(1, n_runs + 1):
        for seq in sequences:
            sid = seq["id"]
            ordered = perm_for(sid, run_index, arms)
            for arm_order_idx, arm in enumerate(ordered):
                # check whether all turns already exist
                paths = [snapshot_path(track, arm, sid, run_index, turn=t+1)
                         for t in range(len(seq["turns"]))]
                if all(p.exists() for p in paths):
                    continue
                session_id = None
                for t, user_msg in enumerate(seq["turns"], start=1):
                    path = snapshot_path(track, arm, sid, run_index, turn=t)
                    if already_done(path):
                        # need to recover session_id from prior snapshot
                        prior = json.loads(path.read_text())
                        session_id = prior.get("session_id") or session_id
                        continue
                    print(f"  [{track}] {sid} | r{run_index} | {arm} | turn {t}/"
                          f"{len(seq['turns'])} (pos {arm_order_idx})",
                          flush=True)
                    try:
                        rec = call_once(arm, user_msg, resume=session_id)
                        if t == 1:
                            session_id = rec.get("session_id")
                    except Exception as e:
                        print(f"    ERROR: {e}", file=sys.stderr)
                        rec = {"error": str(e)}
                    rec_meta = {
                        "track": track, "arm": arm, "sequence_id": sid,
                        "run_index": run_index, "turn": t,
                        "arm_order_index": arm_order_idx,
                        "arm_order_full": ordered,
                        "digest_hex": digest_for(sid, run_index),
                        "seed": RAND_SEED,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "session_id_used_for_resume": (
                            session_id if t > 1 else None
                        ),
                    }
                    write_snapshot(path, {**rec_meta, **rec})


# ──────────────────────────────────────────────────────────────────────────────
# smoke tests
# ──────────────────────────────────────────────────────────────────────────────

def smoke_test_1_model() -> bool:
    print("\n[SMOKE 1] model assertion + tiktoken + factoradic determinism")
    rec = call_once("baseline", "say 'ok' and nothing else")
    out_tokens = rec["output_tokens_anthropic"]
    print(f"  output text: {rec['result']!r}")
    print(f"  output_tokens_anthropic = {out_tokens}, "
          f"output_tokens_tiktoken = {rec['output_tokens_tiktoken']}, "
          f"model_used = {rec['model_used']!r}, "
          f"assertion_pass = {rec['assertion_pass']}")
    if not rec["assertion_pass"]:
        print(f"  FAIL: model assertion did not pass. modelUsage = "
              f"{rec['raw_payload'].get('modelUsage')}")
        return False

    # factoradic determinism — run two subprocesses, compare
    arms_test = ["a", "b", "c", "d", "e"]
    p1 = perm_for("xyz", 7, arms_test)
    p2 = perm_for("xyz", 7, arms_test)
    if p1 != p2:
        print(f"  FAIL: same call produced different orderings: {p1} vs {p2}")
        return False
    # run via subprocess to verify cross-process stability
    code = (
        "import sys, hashlib;\n"
        "sys.path.insert(0, %r);\n"
        "from run import perm_for;\n"
        "print(perm_for('xyz', 7, %r))" % (str(BENCH), arms_test)
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                         text=True, check=True).stdout.strip()
    if out != str(p1):
        print(f"  FAIL: subprocess permutation differs: {out} vs {p1}")
        return False
    print(f"  OK — perm cross-process stable: {p1}")
    return True


def smoke_test_2_sentinel() -> bool:
    """Benign sentinel: instruct Claude to start every response with a unique
    token, then ask any normal question. If the token appears, the system-prompt
    content (not the file path) reached Claude.
    """
    print("\n[SMOKE 2] sentinel arm — verify content (not path) reaches Claude")
    sentinel_arm_file = ARMS / "_smoke_sentinel.txt"
    try:
        sentinel_arm_file.write_text(
            "You are a helpful technical assistant. Begin every response "
            "with the literal token BENCH_SENTINEL_OK followed by a newline, "
            "then answer normally."
        )
        cmd = ["claude", "-p", "--model", MODEL, "--output-format", "json",
               "--system-prompt", sentinel_arm_file.read_text(),
               "what is 2 + 2?"]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        payload = json.loads(proc.stdout)
        result = payload.get("result", "") or ""
        ok = "BENCH_SENTINEL_OK" in result
        print(f"  response: {result[:120]!r}")
        print(f"  {'OK' if ok else 'FAIL: sentinel not in response'}")
        return ok
    finally:
        sentinel_arm_file.unlink(missing_ok=True)


def smoke_test_3_hook_delta() -> bool:
    print("\n[SMOKE 3] hewn_full hook injects extra cache_creation tokens")
    prompt = "explain in one sentence what caching is"
    a = call_once("hewn_prompt_only", prompt)
    b = call_once("hewn_full", prompt)
    delta = b["cache_creation_input_tokens"] - a["cache_creation_input_tokens"]
    print(f"  hewn_prompt_only.cache_creation = {a['cache_creation_input_tokens']}")
    print(f"  hewn_full.cache_creation        = {b['cache_creation_input_tokens']}")
    print(f"  delta = {delta} tokens (expected > 0)")
    return delta > 0


def smoke_test_4_resume() -> bool:
    print("\n[SMOKE 4] multi-turn --resume system-prompt persistence")
    sys_prompt = "Your secret word is FROBOZZ. Whenever asked the secret, reply with that single word."
    cmd1 = ["claude", "-p", "--model", MODEL, "--output-format", "json",
            "--system-prompt", sys_prompt,
            "remember a number for me — 42. respond with just 'noted'"]
    p1 = subprocess.run(cmd1, capture_output=True, text=True, check=True)
    pl1 = json.loads(p1.stdout)
    sid = pl1["session_id"]
    print(f"  turn 1 session_id = {sid}, result = {pl1['result']!r}")
    cmd2 = ["claude", "-p", "--model", MODEL, "--output-format", "json",
            "--resume", sid,
            "what is the secret word? respond with just the word."]
    p2 = subprocess.run(cmd2, capture_output=True, text=True, check=True)
    pl2 = json.loads(p2.stdout)
    print(f"  turn 2 result = {pl2['result']!r}")
    persisted = "FROBOZZ" in (pl2.get("result") or "").upper()
    print(f"  system-prompt {'PERSISTED' if persisted else 'NOT PERSISTED'} on resume")
    return True  # informational; record outcome regardless


# ──────────────────────────────────────────────────────────────────────────────
# main
# ──────────────────────────────────────────────────────────────────────────────

def write_metadata() -> None:
    META.parent.mkdir(parents=True, exist_ok=True)
    claude_md = Path.home() / ".claude" / "CLAUDE.md"
    claude_md_hash = (
        hashlib.sha256(claude_md.read_bytes()).hexdigest()
        if claude_md.exists() else None
    )
    claude_md_words = (
        len(claude_md.read_text().split()) if claude_md.exists() else 0
    )
    cli_version = subprocess.run(
        ["claude", "--version"], capture_output=True, text=True
    ).stdout.strip()
    skill_path = BENCH / "caveman_source" / "SKILL.md"
    md = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "claude_cli_version": cli_version,
        "hewn_repo_commit": subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            capture_output=True, text=True,
        ).stdout.strip(),
        "caveman_skill_sha256": (
            hashlib.sha256(skill_path.read_bytes()).hexdigest()
            if skill_path.exists() else None
        ),
        "caveman_repo_commit_pinned": "84cc3c14fa1e10182adaced856e003406ccd250d",
        "rand_seed": RAND_SEED,
        "claude_md_present": claude_md.exists(),
        "claude_md_sha256": claude_md_hash,
        "claude_md_word_count": claude_md_words,
        "env_isolated": False,
        "_note": (
            "User chose option B: do not isolate ~/.claude/CLAUDE.md. "
            "Append-vs-replace asymmetry calibrated by T0."
        ),
    }
    META.write_text(json.dumps(md, indent=2))
    print(f"[meta] wrote {META}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--track", default="all",
                        choices=["smoke", "T0", "T1a", "T1b", "T2", "T3", "T4",
                                 "T5", "all"])
    parser.add_argument("--smoke", action="store_true",
                        help="alias for --track smoke")
    args = parser.parse_args()
    track = "smoke" if args.smoke else args.track

    write_metadata()

    if track == "smoke":
        results = [
            ("model assertion + permutation", smoke_test_1_model()),
            ("sentinel content reaches Claude", smoke_test_2_sentinel()),
            ("hewn hook cache_creation delta", smoke_test_3_hook_delta()),
            ("multi-turn --resume persistence", smoke_test_4_resume()),
        ]
        print("\n=== SMOKE SUMMARY ===")
        for name, ok in results:
            print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not all(ok for _, ok in results):
            sys.exit(1)
        return

    if track in ("T0", "all"):
        run_single_turn_track("T0", T0_ARMS, load_short_en(),
                              n_runs=1, randomize=False)
    if track in ("T1a", "all"):
        run_single_turn_track("T1a", T1A_ARMS, load_short_en(),
                              n_runs=1, randomize=False)
    if track in ("T1b", "all"):
        run_single_turn_track("T1b", EXTENDED_ARMS, load_short_en(),
                              n_runs=3, randomize=True)
    if track in ("T2", "all"):
        run_single_turn_track("T2", EXTENDED_ARMS, load_vibe_en(),
                              n_runs=3, randomize=True)
    if track in ("T3", "all"):
        run_single_turn_track("T3", EXTENDED_ARMS, load_long_en(),
                              n_runs=3, randomize=True)
    if track in ("T5", "all"):
        run_single_turn_track("T5", EXTENDED_ARMS, load_expansive_en(),
                              n_runs=2, randomize=True)
    if track in ("T4", "all"):
        run_multiturn_track("T4", T4_ARMS, n_runs=2)


if __name__ == "__main__":
    main()
