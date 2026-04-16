from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .normalize import normalize_document_text, repair_direct_sigil_text
from .parser import SIGILParseError, parse_document
from .render import generate_audit
from .schema_transport import load_schema_definition, render_schema_payload


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = ROOT / ".env"


@dataclass(slots=True)
class Variant:
    name: str
    prompt_path: Path
    structured_expected: bool
    transport: str
    draft_prompt_path: Path | None = None
    category: str | None = None


DIRECT_SIGIL_STOP_SEQUENCES = (
    "[AUDIT]",
    "Goal:",
    "Constraints:",
    "Hypothesis:",
    "Plan:",
)


def parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[len("export ") :].strip()
    if "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return key, value


def load_env_file(path: Path) -> dict[str, str]:
    loaded: dict[str, str] = {}
    if not path.exists():
        return loaded
    for line in path.read_text(encoding="utf-8").splitlines():
        parsed = parse_env_line(line)
        if parsed is None:
            continue
        key, value = parsed
        loaded[key] = value
    return loaded


def resolve_runtime_env(env_file: Path | None) -> dict[str, str]:
    runtime = dict(os.environ)
    if env_file is None:
        return runtime
    for key, value in load_env_file(env_file).items():
        runtime.setdefault(key, value)
    return runtime


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            rows.append(json.loads(stripped))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_number}: invalid JSONL row: {exc}") from exc
    return rows


def infer_variant_category(name: str, prompt_path: Path | None = None) -> str | None:
    haystack = f"{name} {prompt_path.name if prompt_path else ''}".lower()
    if "debug" in haystack:
        return "debugging"
    if "arch" in haystack or "architecture" in haystack:
        return "architecture"
    if "review" in haystack:
        return "code_review"
    if "refactor" in haystack:
        return "refactoring"
    return None


def parse_variant(spec: str) -> Variant:
    if "=" not in spec:
        raise argparse.ArgumentTypeError("Variant must use the form name=path/to/prompt.txt")
    name_spec, path_str = spec.split("=", 1)
    name_spec = name_spec.strip()
    prompt_path: Path
    draft_prompt_path: Path | None = None
    if "@" in name_spec:
        name, kind = name_spec.split("@", 1)
        kind = kind.strip().lower()
        if kind in {"plain", "structured"}:
            structured_expected = kind != "plain"
            transport = kind
            prompt_path = (ROOT / path_str.strip()).resolve()
        elif kind == "sigil":
            structured_expected = True
            transport = kind
            prompt_path = (ROOT / path_str.strip()).resolve()
        elif kind.startswith("schema-") and len(kind) > len("schema-"):
            structured_expected = True
            transport = kind
            prompt_path = (ROOT / path_str.strip()).resolve()
        elif kind.startswith("draft2schema-") and len(kind) > len("draft2schema-"):
            structured_expected = True
            transport = kind
            if "::" not in path_str:
                raise argparse.ArgumentTypeError(
                    "draft2schema variants must use name@draft2schema-<schema>=path/to/draft.txt::path/to/schema_prompt.txt"
                )
            draft_path_str, prompt_path_str = path_str.split("::", 1)
            draft_prompt_path = (ROOT / draft_path_str.strip()).resolve()
            prompt_path = (ROOT / prompt_path_str.strip()).resolve()
        else:
            raise argparse.ArgumentTypeError(
                "Variant kind must be 'plain', 'structured', 'sigil', 'schema-<name>', or 'draft2schema-<name>'"
            )
    else:
        name = name_spec
        structured_expected = name.startswith("sigil")
        transport = "structured" if structured_expected else "plain"
        prompt_path = (ROOT / path_str.strip()).resolve()
    name = name.strip()
    if not name:
        raise argparse.ArgumentTypeError("Variant name cannot be empty")
    if not prompt_path.exists():
        raise argparse.ArgumentTypeError(f"Prompt file not found: {prompt_path}")
    if draft_prompt_path is not None and not draft_prompt_path.exists():
        raise argparse.ArgumentTypeError(f"Draft prompt file not found: {draft_prompt_path}")
    return Variant(
        name=name,
        prompt_path=prompt_path,
        structured_expected=structured_expected,
        transport=transport,
        draft_prompt_path=draft_prompt_path,
        category=infer_variant_category(name, prompt_path),
    )


def strip_wrapping_code_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) < 2:
        return stripped
    if not lines[0].startswith("```"):
        return stripped
    if lines[-1].strip() != "```":
        return stripped
    return "\n".join(lines[1:-1]).strip()


def schema_name_from_transport(transport: str) -> str | None:
    for prefix in ("schema-", "draft2schema-"):
        if transport.startswith(prefix):
            return transport.split("-", 1)[1]
    return None


def direct_sigil_stop_sequences(transport: str) -> list[str]:
    if transport != "sigil":
        return []
    return list(DIRECT_SIGIL_STOP_SEQUENCES)


def materialize_direct_sigil(output_text: str, category: str | None = None) -> str:
    stripped = strip_wrapping_code_fences(output_text)
    direct_repaired = repair_direct_sigil_text(stripped, category)
    candidates = [direct_repaired]
    repaired = normalize_document_text(stripped)
    if direct_repaired not in candidates:
        candidates.append(direct_repaired)
    if repaired != stripped and repaired not in candidates:
        candidates.append(repaired)
    if stripped not in candidates:
        candidates.append(stripped)
    for candidate in candidates:
        try:
            document = parse_document(candidate)
        except SIGILParseError:
            document = None
        if document is None and "[AUDIT]" not in candidate:
            placeholder = "[local audit placeholder]"
            try:
                document = parse_document(f"{candidate.rstrip()}\n\n[AUDIT]\n{placeholder}")
            except SIGILParseError:
                continue
            document.audit = ""
            audit = generate_audit(document).strip()
            if not audit:
                return candidate
            return f"{candidate.rstrip()}\n\n[AUDIT]\n{audit}"
        if document is None:
            continue
        if document.audit:
            return candidate
        audit = generate_audit(document).strip()
        if not audit:
            return candidate
        return f"{candidate.rstrip()}\n\n[AUDIT]\n{audit}"
    return stripped


def decode_variant_output(variant: Variant, output_text: str | dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    if isinstance(output_text, dict):
        output_text = str(output_text.get("output_text") or "")
    if variant.transport == "sigil":
        return materialize_direct_sigil(output_text, category=variant.category), None
    schema_name = schema_name_from_transport(variant.transport)
    if schema_name is None:
        return output_text, None
    raw_data = json.loads(output_text)
    rendered = render_schema_payload(raw_data, schema_name=schema_name)
    return rendered, raw_data


def merge_usage(usages: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {"stage_count": len(usages)}
    for key in ("input_tokens", "output_tokens", "total_tokens", "cached_tokens", "reasoning_tokens"):
        values = [usage[key] for usage in usages if usage.get(key) is not None]
        merged[key] = sum(values) if values else None
    return merged


def build_conditioned_task_prompt(task_prompt: str, draft_text: str) -> str:
    return (
        f"{task_prompt}\n\n"
        "Draft candidate from an earlier unconstrained pass:\n"
        "<draft>\n"
        f"{draft_text.strip()}\n"
        "</draft>\n\n"
        "Use the draft for semantic guidance when it is helpful, but prefer the task prompt if they conflict. "
        "Return only the final schema-compliant output."
    )


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def openai_text_format_for_transport(transport: str) -> dict[str, Any] | None:
    schema_name = schema_name_from_transport(transport)
    if schema_name is None:
        return None
    return load_schema_definition(schema_name)


def _to_gemini_schema(value: Any) -> Any:
    if isinstance(value, dict):
        transformed: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"additionalProperties", "$schema", "strict", "name"}:
                continue
            if key == "items" and item is False:
                continue
            transformed[key] = _to_gemini_schema(item)
        return transformed
    if isinstance(value, list):
        return [_to_gemini_schema(item) for item in value]
    return value


def gemini_generation_config(
    max_output_tokens: int,
    transport: str,
    thinking_budget: int | None = None,
    stop_sequences: list[str] | None = None,
) -> dict[str, Any]:
    config: dict[str, Any] = {"maxOutputTokens": max_output_tokens}
    schema_name = schema_name_from_transport(transport)
    if schema_name is not None:
        schema_def = load_schema_definition(schema_name)
        config["responseMimeType"] = "application/json"
        config["responseSchema"] = _to_gemini_schema(schema_def["schema"])
    if thinking_budget is not None:
        config["thinkingConfig"] = {"thinkingBudget": thinking_budget}
    if stop_sequences:
        config["stopSequences"] = stop_sequences
    return config
