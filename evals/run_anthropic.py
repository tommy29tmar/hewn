from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sigil.eval_common import (
    DEFAULT_ENV_FILE,
    append_jsonl,
    decode_variant_output,
    direct_sigil_stop_sequences,
    load_jsonl,
    parse_variant,
    resolve_runtime_env,
)


DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
DEFAULT_ANTHROPIC_VERSION = "2023-06-01"


def should_retry_http_status(status_code: int) -> bool:
    return status_code in {408, 409, 429, 500, 502, 503, 504}


def build_payload(
    *,
    model: str,
    task_prompt: str,
    instructions: str,
    max_output_tokens: int,
    thinking_budget: int | None,
    cache_system_prompt: bool,
    cache_prefix: str | None = None,
    stop_sequences: list[str] | None = None,
) -> dict[str, Any]:
    system_block: list[dict[str, Any]] = [{"type": "text", "text": instructions}]
    if cache_prefix:
        system_block.append({"type": "text", "text": cache_prefix, "cache_control": {"type": "ephemeral"}})
    elif cache_system_prompt:
        system_block[0]["cache_control"] = {"type": "ephemeral"}
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": max_output_tokens,
        "system": system_block,
        "messages": [{"role": "user", "content": [{"type": "text", "text": task_prompt}]}],
    }
    if thinking_budget is not None:
        payload["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
    if stop_sequences:
        payload["stop_sequences"] = stop_sequences
    return payload


def call_messages_api(
    *,
    api_key: str,
    base_url: str,
    anthropic_version: str,
    payload: dict[str, Any],
    timeout: int,
    max_retries: int = 0,
    retry_backoff_seconds: float = 1.5,
) -> dict[str, Any]:
    base_url = base_url.rstrip("/")
    req = request.Request(
        url=f"{base_url}/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": anthropic_version,
            "content-type": "application/json",
        },
        method="POST",
    )
    attempt = 0
    while True:
        try:
            with request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if attempt < max_retries and should_retry_http_status(exc.code):
                time.sleep(retry_backoff_seconds * (2**attempt))
                attempt += 1
                continue
            raise SystemExit(f"Anthropic API error {exc.code}: {body}") from exc
        except error.URLError as exc:
            if attempt < max_retries:
                time.sleep(retry_backoff_seconds * (2**attempt))
                attempt += 1
                continue
            raise SystemExit(f"Network error calling Anthropic API: {exc}") from exc


def extract_output_text(response: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in response.get("content", []):
        if block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(part for part in parts if part).strip()


def extract_usage(response: dict[str, Any]) -> dict[str, Any]:
    usage = response.get("usage") or {}
    cache_creation = usage.get("cache_creation_input_tokens") or 0
    cache_read = usage.get("cache_read_input_tokens") or 0
    raw_input = usage.get("input_tokens") or 0
    input_tokens = raw_input + cache_creation + cache_read
    output_tokens = usage.get("output_tokens")
    total_tokens = input_tokens + output_tokens if output_tokens is not None else None
    return {
        "input_tokens": input_tokens if input_tokens else None,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cached_tokens": cache_read or None,
        "reasoning_tokens": usage.get("thinking_tokens"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run SIGIL eval prompts against the Anthropic Messages API.")
    parser.add_argument("--tasks", type=Path, default=ROOT / "evals" / "tasks.jsonl")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--variant", dest="variants", action="append", type=parse_variant, required=True)
    parser.add_argument("--max-output-tokens", type=int, default=800)
    parser.add_argument("--thinking-budget", type=int, default=None)
    parser.add_argument("--task-id", dest="task_ids", action="append", default=None)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--anthropic-version", default=DEFAULT_ANTHROPIC_VERSION)
    parser.add_argument("--cache-system-prompt", action="store_true")
    parser.add_argument("--cache-task-prefix", action="store_true", help="Move task cache_prefix into a cacheable system block and send only prompt_suffix as the user message.")
    parser.add_argument("--max-retries", type=int, default=0)
    parser.add_argument("--retry-backoff-seconds", type=float, default=1.5)
    args = parser.parse_args(argv)

    runtime_env = resolve_runtime_env(args.env_file)
    api_key = runtime_env.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY is not set.")
    base_url = args.base_url or runtime_env.get("ANTHROPIC_BASE_URL") or DEFAULT_BASE_URL

    for variant in args.variants:
        if variant.transport not in {"plain", "sigil"}:
            raise SystemExit(
                f"Anthropic runner currently supports only plain or direct SIGIL variants; got {variant.transport}."
            )

    tasks = load_jsonl(args.tasks)
    if args.task_ids:
        selected = set(args.task_ids)
        tasks = [task for task in tasks if str(task["id"]) in selected]
        missing = selected.difference(str(task["id"]) for task in tasks)
        if missing:
            raise SystemExit(f"Unknown task ids: {', '.join(sorted(missing))}")

    if args.overwrite and args.out.exists():
        args.out.unlink()

    prompt_cache = {variant.prompt_path: variant.prompt_path.read_text(encoding="utf-8") for variant in args.variants}
    total = len(tasks) * len(args.variants)
    completed = 0
    for task in tasks:
        task_id = str(task["id"])
        task_prompt = str(task["prompt"])
        prompt_suffix = str(task.get("prompt_suffix") or task_prompt)
        cache_prefix = str(task.get("cache_prefix") or "").strip()
        for variant in args.variants:
            completed += 1
            print(f"[{completed}/{total}] {task_id} :: {variant.name}", file=sys.stderr)
            started_at = time.perf_counter()
            task_prompt_text = prompt_suffix if (args.cache_task_prefix and cache_prefix) else task_prompt
            payload = build_payload(
                model=args.model,
                task_prompt=task_prompt_text,
                instructions=prompt_cache[variant.prompt_path],
                max_output_tokens=args.max_output_tokens,
                thinking_budget=args.thinking_budget,
                cache_system_prompt=args.cache_system_prompt,
                cache_prefix=cache_prefix if args.cache_task_prefix and cache_prefix else None,
                stop_sequences=direct_sigil_stop_sequences(variant.transport),
            )
            response = call_messages_api(
                api_key=api_key,
                base_url=base_url,
                anthropic_version=args.anthropic_version,
                payload=payload,
                timeout=args.timeout,
                max_retries=args.max_retries,
                retry_backoff_seconds=args.retry_backoff_seconds,
            )
            output_text = extract_output_text(response)
            content, structured_data = decode_variant_output(variant, output_text)
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            row = {
                "task_id": task_id,
                "variant": variant.name,
                "model": args.model,
                "provider": "anthropic",
                "prompt_path": str(variant.prompt_path.relative_to(ROOT)),
                "draft_prompt_path": None,
                "structured_expected": variant.structured_expected,
                "content": content,
                "transport": variant.transport,
                "usage": {"stage_count": 1, **extract_usage(response)},
                "stage_usages": [extract_usage(response)],
                "elapsed_ms": elapsed_ms,
                "response_id": response.get("id"),
                "status": response.get("stop_reason"),
            }
            if structured_data is not None:
                row["structured_data"] = structured_data
            append_jsonl(args.out, row)
            if args.sleep_seconds:
                time.sleep(args.sleep_seconds)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
