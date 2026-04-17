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

from flint.eval_common import (
    DEFAULT_ENV_FILE,
    append_jsonl,
    build_conditioned_task_prompt,
    decode_variant_output,
    load_jsonl,
    merge_usage,
    openai_text_format_for_transport as load_schema_definition,
    parse_env_line,
    parse_variant,
    resolve_runtime_env,
    schema_name_from_transport,
    strip_wrapping_code_fences,
)


def build_payload(
    *,
    model: str,
    task_prompt: str,
    instructions: str,
    max_output_tokens: int,
    reasoning_effort: str | None,
    reasoning_summary: str | None,
    verbosity: str | None,
    text_format: dict[str, Any] | None,
    prompt_cache_key: str | None,
    prompt_cache_retention: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "instructions": instructions,
        "input": task_prompt,
        "max_output_tokens": max_output_tokens,
        "store": False,
    }
    if prompt_cache_key:
        payload["prompt_cache_key"] = prompt_cache_key
    if prompt_cache_retention:
        payload["prompt_cache_retention"] = prompt_cache_retention
    if reasoning_effort or reasoning_summary:
        reasoning: dict[str, Any] = {}
        if reasoning_effort:
            reasoning["effort"] = reasoning_effort
        if reasoning_summary:
            reasoning["summary"] = reasoning_summary
        payload["reasoning"] = reasoning
    text_block: dict[str, Any] = {}
    if verbosity:
        text_block["verbosity"] = verbosity
    if text_format:
        text_block["format"] = text_format
    if text_block:
        payload["text"] = text_block
    return payload


def should_retry_http_status(status_code: int) -> bool:
    return status_code in {408, 409, 429, 500, 502, 503, 504}


def call_responses_api(
    *,
    api_key: str,
    base_url: str,
    payload: dict[str, Any],
    timeout: int,
    max_retries: int = 0,
    retry_backoff_seconds: float = 1.5,
) -> dict[str, Any]:
    base_url = base_url.rstrip("/")
    req = request.Request(
        url=f"{base_url}/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
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
            raise SystemExit(f"OpenAI API error {exc.code}: {body}") from exc
        except error.URLError as exc:
            if attempt < max_retries:
                time.sleep(retry_backoff_seconds * (2**attempt))
                attempt += 1
                continue
            raise SystemExit(f"Network error calling OpenAI API: {exc}") from exc


def extract_output_text(response: dict[str, Any]) -> str:
    output_text = response.get("output_text")
    if isinstance(output_text, str) and output_text:
        return output_text

    pieces: list[str] = []
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str):
                    pieces.append(text)
    return "\n".join(piece for piece in pieces if piece).strip()

def extract_usage(response: dict[str, Any]) -> dict[str, Any]:
    usage = response.get("usage") or {}
    input_details = usage.get("input_tokens_details") or {}
    output_details = usage.get("output_tokens_details") or {}
    return {
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "cached_tokens": input_details.get("cached_tokens"),
        "reasoning_tokens": output_details.get("reasoning_tokens"),
    }

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run SIGIL eval prompts against the OpenAI Responses API.")
    parser.add_argument("--tasks", type=Path, default=ROOT / "evals" / "tasks.jsonl")
    parser.add_argument("--out", type=Path, required=True, help="JSONL file to append run rows to.")
    parser.add_argument("--model", required=True, help="Model id, for example gpt-5.2 or gpt-5.2-mini.")
    parser.add_argument(
        "--variant",
        dest="variants",
        action="append",
        type=parse_variant,
        required=True,
        help=(
            "Variant definition in the form "
            "name[@plain|@structured|@schema-hybrid|@schema-memory|@schema-compile]=prompts/file.txt "
            "or name@draft2schema-<schema>=prompts/draft.txt::prompts/schema_prompt.txt. Repeat for multiple variants."
        ),
    )
    parser.add_argument("--max-output-tokens", type=int, default=800)
    parser.add_argument("--reasoning-effort", choices=["none", "minimal", "low", "medium", "high", "xhigh"], default=None)
    parser.add_argument("--reasoning-summary", choices=["auto", "concise", "detailed"], default=None)
    parser.add_argument("--verbosity", choices=["low", "medium", "high"], default=None)
    parser.add_argument("--task-id", dest="task_ids", action="append", default=None, help="Limit to specific task ids. Repeatable.")
    parser.add_argument("--sleep-seconds", type=float, default=0.0, help="Sleep between requests to reduce burstiness.")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--overwrite", action="store_true", help="Delete the output file before writing.")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE, help="Local env file to load if process env is missing keys.")
    parser.add_argument("--base-url", default=None, help="Override the Responses API base URL. Defaults to OPENAI_BASE_URL or https://api.openai.com/v1.")
    parser.add_argument("--prompt-cache-key", default=None, help="Optional prompt cache key for repeated benchmark prefixes.")
    parser.add_argument("--prompt-cache-retention", choices=["in-memory", "24h"], default=None, help="Optional prompt cache retention policy.")
    parser.add_argument("--max-retries", type=int, default=0, help="Retry transient provider failures this many times.")
    parser.add_argument("--retry-backoff-seconds", type=float, default=1.5, help="Base backoff for provider retries.")
    args = parser.parse_args(argv)

    runtime_env = resolve_runtime_env(args.env_file)
    api_key = runtime_env.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is not set.")
    base_url = args.base_url or runtime_env.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"

    tasks = load_jsonl(args.tasks)
    if args.task_ids:
        selected = set(args.task_ids)
        tasks = [task for task in tasks if str(task["id"]) in selected]
        missing = selected.difference(str(task["id"]) for task in tasks)
        if missing:
            raise SystemExit(f"Unknown task ids: {', '.join(sorted(missing))}")

    if args.overwrite and args.out.exists():
        args.out.unlink()

    prompt_cache: dict[Path, str] = {}
    for variant in args.variants:
        prompt_cache[variant.prompt_path] = variant.prompt_path.read_text(encoding="utf-8")
        if variant.draft_prompt_path is not None:
            prompt_cache[variant.draft_prompt_path] = variant.draft_prompt_path.read_text(encoding="utf-8")

    total = len(tasks) * len(args.variants)
    completed = 0
    for task in tasks:
        task_id = str(task["id"])
        task_prompt = str(task["prompt"])
        for variant in args.variants:
            completed += 1
            print(f"[{completed}/{total}] {task_id} :: {variant.name}", file=sys.stderr)
            started_at = time.perf_counter()
            stage_usages: list[dict[str, Any]] = []
            structured_data = None
            draft_content = None
            final_task_prompt = task_prompt
            if variant.transport.startswith("draft2schema-"):
                assert variant.draft_prompt_path is not None
                draft_payload = build_payload(
                    model=args.model,
                    task_prompt=task_prompt,
                    instructions=prompt_cache[variant.draft_prompt_path],
                    max_output_tokens=min(args.max_output_tokens, 240),
                    reasoning_effort=args.reasoning_effort,
                    reasoning_summary=None,
                    verbosity=args.verbosity,
                    text_format=None,
                    prompt_cache_key=args.prompt_cache_key,
                    prompt_cache_retention=args.prompt_cache_retention,
                )
                draft_response = call_responses_api(
                    api_key=api_key,
                    base_url=base_url,
                    payload=draft_payload,
                    timeout=args.timeout,
                    max_retries=args.max_retries,
                    retry_backoff_seconds=args.retry_backoff_seconds,
                )
                draft_content = strip_wrapping_code_fences(extract_output_text(draft_response))
                stage_usages.append(extract_usage(draft_response))
                final_task_prompt = build_conditioned_task_prompt(task_prompt, draft_content)

            instructions = prompt_cache[variant.prompt_path]
            text_format = None
            schema_name = schema_name_from_transport(variant.transport)
            if schema_name is not None:
                text_format = load_schema_definition(variant.transport)
            payload = build_payload(
                model=args.model,
                task_prompt=final_task_prompt,
                instructions=instructions,
                max_output_tokens=args.max_output_tokens,
                reasoning_effort=args.reasoning_effort,
                reasoning_summary=args.reasoning_summary,
                verbosity=args.verbosity,
                text_format=text_format,
                prompt_cache_key=args.prompt_cache_key,
                prompt_cache_retention=args.prompt_cache_retention,
            )
            response = call_responses_api(
                api_key=api_key,
                base_url=base_url,
                payload=payload,
                timeout=args.timeout,
                max_retries=args.max_retries,
                retry_backoff_seconds=args.retry_backoff_seconds,
            )
            content, structured_data = decode_variant_output(variant, extract_output_text(response))
            stage_usages.append(extract_usage(response))
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            row = {
                "task_id": task_id,
                "variant": variant.name,
                "model": args.model,
                "prompt_path": str(variant.prompt_path.relative_to(ROOT)),
                "draft_prompt_path": str(variant.draft_prompt_path.relative_to(ROOT)) if variant.draft_prompt_path else None,
                "structured_expected": variant.structured_expected,
                "content": content,
                "transport": variant.transport,
                "usage": merge_usage(stage_usages),
                "stage_usages": stage_usages,
                "elapsed_ms": elapsed_ms,
                "response_id": response.get("id"),
                "status": response.get("status"),
            }
            if draft_content is not None:
                row["draft_content"] = draft_content
            if structured_data is not None:
                row["structured_data"] = structured_data
            append_jsonl(args.out, row)
            if args.sleep_seconds:
                time.sleep(args.sleep_seconds)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
