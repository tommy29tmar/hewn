from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flint.eval_common import (
    DEFAULT_ENV_FILE,
    append_jsonl,
    build_cached_task_prompt,
    decode_variant_output,
    direct_flint_stop_sequences,
    gemini_generation_config,
    load_jsonl,
    parse_variant,
    resolve_runtime_env,
)


DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def should_retry_http_status(status_code: int) -> bool:
    return status_code in {408, 409, 429, 500, 502, 503, 504}


def build_payload(
    *,
    task_prompt: str,
    instructions: str,
    max_output_tokens: int,
    transport: str,
    thinking_budget: int | None,
    cached_content_name: str | None = None,
    stop_sequences: list[str] | None = None,
) -> dict[str, Any]:
    payload = {
        "contents": [{"role": "user", "parts": [{"text": task_prompt}]}],
        "generationConfig": gemini_generation_config(
            max_output_tokens,
            transport,
            thinking_budget,
            stop_sequences=stop_sequences,
        ),
    }
    if cached_content_name:
        payload["cachedContent"] = cached_content_name
    else:
        payload["systemInstruction"] = {"parts": [{"text": instructions}]}
    return payload


def normalize_cache_model_name(model: str) -> str:
    return model if model.startswith("models/") else f"models/{model}"


def build_cache_payload(
    *,
    model: str,
    instructions: str,
    cache_prefix: str,
    ttl: str,
    display_name: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": normalize_cache_model_name(model),
        "systemInstruction": {"parts": [{"text": instructions}]},
        "contents": [{"role": "user", "parts": [{"text": cache_prefix}]}],
        "ttl": ttl,
    }
    if display_name:
        payload["displayName"] = display_name
    return payload


def call_generate_content(
    *,
    api_key: str,
    base_url: str,
    model: str,
    payload: dict[str, Any],
    timeout: int,
    max_retries: int = 0,
    retry_backoff_seconds: float = 1.5,
) -> dict[str, Any]:
    base_url = base_url.rstrip("/")
    url = f"{base_url}/models/{model}:generateContent?{parse.urlencode({'key': api_key})}"
    req = request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
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
            raise SystemExit(f"Gemini API error {exc.code}: {body}") from exc
        except error.URLError as exc:
            if attempt < max_retries:
                time.sleep(retry_backoff_seconds * (2**attempt))
                attempt += 1
                continue
            raise SystemExit(f"Network error calling Gemini API: {exc}") from exc


def call_create_cached_content(
    *,
    api_key: str,
    base_url: str,
    payload: dict[str, Any],
    timeout: int,
    max_retries: int = 0,
    retry_backoff_seconds: float = 1.5,
) -> dict[str, Any]:
    base_url = base_url.rstrip("/")
    url = f"{base_url}/cachedContents?{parse.urlencode({'key': api_key})}"
    req = request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
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
            raise SystemExit(f"Gemini cache API error {exc.code}: {body}") from exc
        except error.URLError as exc:
            if attempt < max_retries:
                time.sleep(retry_backoff_seconds * (2**attempt))
                attempt += 1
                continue
            raise SystemExit(f"Network error creating Gemini cached content: {exc}") from exc


def extract_output_text(response: dict[str, Any]) -> str:
    parts: list[str] = []
    candidates = response.get("candidates") or []
    if not candidates:
        return ""
    for part in ((candidates[0].get("content") or {}).get("parts") or []):
        text = part.get("text")
        if isinstance(text, str):
            parts.append(text)
    return "\n".join(part for part in parts if part).strip()


def extract_usage(response: dict[str, Any]) -> dict[str, Any]:
    usage = response.get("usageMetadata") or {}
    prompt_tokens = usage.get("promptTokenCount")
    output_tokens = usage.get("candidatesTokenCount")
    return {
        "input_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "total_tokens": usage.get("totalTokenCount"),
        "cached_tokens": usage.get("cachedContentTokenCount"),
        "reasoning_tokens": usage.get("thoughtsTokenCount"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run SIGIL eval prompts against the Gemini generateContent API.")
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
    parser.add_argument("--max-retries", type=int, default=0)
    parser.add_argument("--retry-backoff-seconds", type=float, default=1.5)
    parser.add_argument("--use-explicit-cache", action="store_true")
    parser.add_argument("--cache-ttl", default="3600s")
    parser.add_argument("--cache-display-name-prefix", default="sigil-eval")
    parser.add_argument("--exclude-cache-create-latency", action="store_true")
    args = parser.parse_args(argv)

    runtime_env = resolve_runtime_env(args.env_file)
    api_key = runtime_env.get("GOOGLE_GENERATIVE_AI_API_KEY") or runtime_env.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GOOGLE_GENERATIVE_AI_API_KEY is not set.")
    base_url = args.base_url or runtime_env.get("GOOGLE_GENERATIVE_AI_BASE_URL") or DEFAULT_BASE_URL

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
    explicit_cache_registry: dict[tuple[str, str, str, str], str] = {}
    total = len(tasks) * len(args.variants)
    completed = 0
    for task in tasks:
        task_id = str(task["id"])
        task_prompt = str(task["prompt"])
        prompt_suffix = str(task.get("prompt_suffix") or task_prompt)
        task_context = str(task.get("task_context") or "").strip()
        cache_prefix = str(task.get("cache_prefix") or "").strip()
        for variant in args.variants:
            completed += 1
            print(f"[{completed}/{total}] {task_id} :: {variant.name}", file=sys.stderr)
            cache_create_ms = None
            cached_content_name = None
            if args.use_explicit_cache and cache_prefix:
                registry_key = (args.model, str(variant.prompt_path), cache_prefix, args.cache_ttl)
                cached_content_name = explicit_cache_registry.get(registry_key)
                if cached_content_name is None:
                    cache_started_at = time.perf_counter()
                    cache_response = call_create_cached_content(
                        api_key=api_key,
                        base_url=base_url,
                        payload=build_cache_payload(
                            model=args.model,
                            instructions=prompt_cache[variant.prompt_path],
                            cache_prefix=cache_prefix,
                            ttl=args.cache_ttl,
                            display_name=f"{args.cache_display_name_prefix}-{task_id}-{variant.name}",
                        ),
                        timeout=args.timeout,
                        max_retries=args.max_retries,
                        retry_backoff_seconds=args.retry_backoff_seconds,
                    )
                    cached_content_name = str(cache_response["name"])
                    explicit_cache_registry[registry_key] = cached_content_name
                    cache_create_ms = round((time.perf_counter() - cache_started_at) * 1000, 2)
            started_at = time.perf_counter()
            payload = build_payload(
                task_prompt=build_cached_task_prompt(prompt_suffix, task_context) if cached_content_name else task_prompt,
                instructions=prompt_cache[variant.prompt_path],
                max_output_tokens=args.max_output_tokens,
                transport=variant.transport,
                thinking_budget=args.thinking_budget,
                cached_content_name=cached_content_name,
                stop_sequences=direct_flint_stop_sequences(variant.transport),
            )
            response = call_generate_content(
                api_key=api_key,
                base_url=base_url,
                model=args.model,
                payload=payload,
                timeout=args.timeout,
                max_retries=args.max_retries,
                retry_backoff_seconds=args.retry_backoff_seconds,
            )
            output_text = extract_output_text(response)
            content, structured_data = decode_variant_output(
                variant,
                output_text,
                task_category=str(task.get("category") or "") or None,
            )
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            finish_reason = None
            candidates = response.get("candidates") or []
            if candidates:
                finish_reason = candidates[0].get("finishReason")
            row = {
                "task_id": task_id,
                "task_category": str(task.get("category") or "") or None,
                "variant": variant.name,
                "model": args.model,
                "provider": "gemini",
                "prompt_path": str(variant.prompt_path.relative_to(ROOT)),
                "draft_prompt_path": None,
                "structured_expected": variant.structured_expected,
                "content": content,
                "transport": variant.transport,
                "usage": {"stage_count": 1, **extract_usage(response)},
                "stage_usages": [extract_usage(response)],
                "elapsed_ms": elapsed_ms,
                "response_id": response.get("responseId"),
                "status": finish_reason,
            }
            if cached_content_name is not None:
                row["cached_content_name"] = cached_content_name
            if cache_create_ms is not None:
                row["cache_create_ms"] = cache_create_ms
                if not args.exclude_cache_create_latency:
                    row["elapsed_ms"] = round(row["elapsed_ms"] + cache_create_ms, 2)
            if structured_data is not None:
                row["structured_data"] = structured_data
            append_jsonl(args.out, row)
            if args.sleep_seconds:
                time.sleep(args.sleep_seconds)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
