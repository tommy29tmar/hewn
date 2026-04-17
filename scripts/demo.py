#!/usr/bin/env python3
"""SIGIL demo — side-by-side comparison of three prompt styles on one question.

Calls Anthropic API three times:
  1. baseline-terse   (prompts/baseline_terse.txt)
  2. primitive-english (prompts/primitive_english.txt, Caveman-style)
  3. sigil-nano       (integrations/claude-code/flint_system_prompt.txt)

Prints side-by-side output with token counts and latency.
Used for launch screenshots and live demos.

Usage:
  python3 scripts/demo.py "Why is this regex too greedy? pattern: .*a"
  python3 scripts/demo.py --model claude-sonnet-4-6 "some question..."
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib import request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]

PROMPTS = {
    "baseline-terse": ROOT / "prompts" / "baseline_terse.txt",
    "primitive-english": ROOT / "prompts" / "primitive_english.txt",
    "sigil-nano": ROOT / "integrations" / "claude-code" / "sigil_system_prompt.txt",
}

COLOR = {
    "reset": "\033[0m",
    "dim": "\033[2m",
    "bold": "\033[1m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "cyan": "\033[36m",
    "magenta": "\033[35m",
    "red": "\033[31m",
}


def load_env() -> dict[str, str]:
    env = {}
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def call_anthropic(api_key: str, model: str, system_prompt: str, user: str, max_tokens: int = 1024) -> dict:
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "system": [{"type": "text", "text": system_prompt}],
        "messages": [{"role": "user", "content": [{"type": "text", "text": user}]}],
    }
    req = request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"API error {e.code}: {e.read().decode(errors='replace')[:400]}")
    elapsed_ms = round((time.perf_counter() - t0) * 1000)
    text = "\n".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    return {
        "text": text.strip(),
        "stop_reason": data.get("stop_reason"),
        "input_tokens": data["usage"]["input_tokens"],
        "output_tokens": data["usage"]["output_tokens"],
        "total_tokens": data["usage"]["input_tokens"] + data["usage"]["output_tokens"],
        "elapsed_ms": elapsed_ms,
    }


def pct(new: int, base: int) -> str:
    if base == 0:
        return "—"
    delta = (new - base) / base * 100
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.1f}%"


def truncate(text: str, max_lines: int = 20) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    return "\n".join(lines[:max_lines]) + f"\n{COLOR['dim']}... ({len(lines) - max_lines} more lines){COLOR['reset']}"


def render_column(title: str, color: str, prompt_name: str, result: dict, base_result: dict | None) -> str:
    header = f"{COLOR['bold']}{color}{title}{COLOR['reset']}"
    meta = [
        f"prompt: {prompt_name}",
        f"input:  {result['input_tokens']} tok",
        f"output: {result['output_tokens']} tok",
        f"total:  {result['total_tokens']} tok",
        f"time:   {result['elapsed_ms']} ms",
    ]
    if base_result is not None:
        meta.append(f"vs terse total: {pct(result['total_tokens'], base_result['total_tokens'])}")
        meta.append(f"vs terse time:  {pct(result['elapsed_ms'], base_result['elapsed_ms'])}")

    out = [header, COLOR['dim'] + "─" * 40 + COLOR['reset']]
    out.extend(COLOR['dim'] + m + COLOR['reset'] for m in meta)
    out.append(COLOR['dim'] + "─" * 40 + COLOR['reset'])
    out.append(truncate(result["text"], max_lines=24))
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="SIGIL 3-way demo.")
    p.add_argument("question", help="The technical question to compare.")
    p.add_argument("--model", default="claude-opus-4-7")
    p.add_argument("--max-tokens", type=int, default=1024)
    p.add_argument("--no-color", action="store_true")
    args = p.parse_args(argv)

    if args.no_color:
        for k in COLOR:
            COLOR[k] = ""

    env = load_env()
    api_key = env.get("ANTHROPIC_API_KEY") or ""
    if not api_key:
        print("error: ANTHROPIC_API_KEY not found in .env", file=sys.stderr)
        return 2

    print(f"{COLOR['bold']}Model:{COLOR['reset']} {args.model}")
    print(f"{COLOR['bold']}Question:{COLOR['reset']} {args.question}")
    print()

    results: dict[str, dict] = {}
    order = ["baseline-terse", "primitive-english", "sigil-nano"]
    colors = {"baseline-terse": COLOR["yellow"], "primitive-english": COLOR["magenta"], "sigil-nano": COLOR["green"]}
    titles = {"baseline-terse": "1. Terse baseline", "primitive-english": "2. Primitive English (Caveman-style)", "sigil-nano": "3. SIGIL"}

    for name in order:
        system = PROMPTS[name].read_text()
        print(f"{COLOR['dim']}calling {name}…{COLOR['reset']}")
        results[name] = call_anthropic(api_key, args.model, system, args.question, args.max_tokens)

    print()
    for name in order:
        print(render_column(titles[name], colors[name], name, results[name], results["baseline-terse"] if name != "baseline-terse" else None))
        print()

    # Summary
    base = results["baseline-terse"]
    sigil = results["sigil-nano"]
    prim = results["primitive-english"]
    print(COLOR['bold'] + "Summary (vs terse baseline):" + COLOR['reset'])
    print(f"  Primitive English total tokens: {pct(prim['total_tokens'], base['total_tokens'])}, time: {pct(prim['elapsed_ms'], base['elapsed_ms'])}")
    print(f"  SIGIL total tokens:             {pct(sigil['total_tokens'], base['total_tokens'])}, time: {pct(sigil['elapsed_ms'], base['elapsed_ms'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
