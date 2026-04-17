from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flint.eval_common import infer_variant_category, materialize_direct_sigil
from flint.schema_transport import render_schema_payload


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


def dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def schema_name_from_transport(transport: str) -> str | None:
    for prefix in ("schema-", "draft2schema-"):
        if transport.startswith(prefix):
            return transport.split("-", 1)[1]
    return None


def rerender_row(row: dict[str, Any]) -> dict[str, Any]:
    transport = str(row.get("transport") or "")
    if transport == "sigil":
        updated = dict(row)
        prompt_path = row.get("prompt_path")
        prompt = Path(str(prompt_path)) if prompt_path else None
        category = infer_variant_category(str(row.get("variant") or ""), prompt)
        updated["content"] = materialize_direct_sigil(str(row.get("content") or ""), category=category)
        return updated
    structured = row.get("structured_data")
    schema_name = schema_name_from_transport(transport)
    if not isinstance(structured, dict) or schema_name is None:
        return row
    updated = dict(row)
    updated["content"] = render_schema_payload(structured, schema_name=schema_name)
    return updated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Re-render structured SIGIL run rows with the current local renderer.")
    parser.add_argument("source", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args(argv)

    rows = load_jsonl(args.source)
    updated = [rerender_row(row) for row in rows]
    dump_jsonl(args.out, updated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
