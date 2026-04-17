from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas"
COMPACT_EXPR_RE = re.compile(
    r"^[A-Za-z0-9_./:+\-\[\]'\"<>]+(?:\((?:[A-Za-z0-9_./:+\-\[\]'\"<>]+|\"[^\"]+\"|'[^']+')"
    r"(?:,(?:[A-Za-z0-9_./:+\-\[\]'\"<>]+|\"[^\"]+\"|'[^']+'))*\))?$"
)
CALL_RE = re.compile(r"^([A-Za-z0-9_./:+\-]+)\((.*)\)$")


def load_schema_definition(name: str) -> dict[str, Any]:
    path = SCHEMA_DIR / f"{name}_schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _render_codebook(entries: list[dict[str, str]]) -> list[str]:
    if not entries:
        return []
    body = [f"  {entry['symbol']}={entry['value']};" for entry in entries]
    return ["@cb[", *body, "]"]


def _join(items: list[str], operator: str) -> str:
    return f" {operator} ".join(item for item in items if item)


def _risk_items(items: list[str]) -> list[str]:
    return [item if item.startswith(("!", "?")) else f"! {item}" for item in items]


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _expand_compact_atom(value: str) -> str:
    stripped = value.strip().lstrip("!?").strip()
    aliases = {
        "bc": "backward compatibility",
        "sec": "security",
        "min_diff": "minimal diff",
        "reg_t": "regression test",
        "skew30": "30-second grace window",
        "exp_lt_no_skew": "strict expiry check without grace window",
        "allow30s_skew": "30-second grace fix",
        "mod_monolith": "modular_monolith",
        "fast_ship": "fast shipping",
        "low_ops": "low ops",
        "future_split_ready": "later split readiness",
        "monolith_now": "ship a modular_monolith now",
        "shared_pg": "shared PostgreSQL",
        "slice_ready_modules": "split-ready modules",
        "hdr_override:authz_bypass": "header auth bypass risk",
        "drop_hdr": "drop the header path",
        "sess_only": "verified session auth only",
        "authz_bypass": "authorization bypass",
        "data_tamper": "data tampering risk",
        "same_order": "same validation order",
        "one_next(err)": "single next(err) path",
        "async_await": "async/await",
        "timeunit_bug": "time unit bug",
        "premature_distrib": "premature distribution",
        "split_cost": "future split cost",
    }
    if stripped in aliases:
        return aliases[stripped]
    if stripped.startswith("edge("):
        if "-30s" in stripped and "200" in stripped:
            return "boundary at minus 30 seconds passes"
        if "-31s" in stripped and "401" in stripped:
            return "boundary at minus 31 seconds returns 401"
        if "-30s" in stripped:
            return "boundary at minus 30 seconds"
    match = CALL_RE.match(stripped)
    if not match:
        return stripped.replace("_", " ")
    name, raw_args = match.groups()
    args = [_strip_quotes(part.strip()) for part in raw_args.split(",") if part.strip()]
    if name == "team" and args:
        return f"team of {args[0]}"
    if name == "ddl" and args:
        return f"deadline {args[0]}"
    if name == "store" and args:
        return args[0]
    if name == "traffic" and args:
        return f"{args[0]} traffic"
    if name == "split" and args and args[0] == "post_release":
        return "split after first release"
    if name == "spoof" and args:
        return f"spoofed {args[0]} header"
    if name == "promisify" and args:
        return f"promisify {args[0]}"
    if name == "await" and args:
        return f"await {args[0]}"
    return stripped.replace("_", " ")


def _expand_atoms(values: list[str], limit: int | None = None) -> list[str]:
    items = [_expand_compact_atom(value) for value in values if value]
    if limit is not None:
        items = items[:limit]
    return items


def _local_audit_debug(target: str, constraints: list[str], tests: list[str]) -> str:
    core = ", ".join(_expand_atoms(constraints, limit=2)) if constraints else "core constraints"
    test = _expand_compact_atom(tests[0]) if tests else "regression test coverage"
    return f"Fix {_expand_compact_atom(target)}, preserve {core}, and add a regression test for the 30-second grace window with {test}."


def _local_audit_architecture(decision: str, constraints: list[str]) -> str:
    expanded = _expand_atoms(constraints)
    team = next((item for item in expanded if item.startswith("team of ")), "the current team")
    deadline = next((item for item in expanded if item.startswith("deadline ")), "the current deadline")
    store = next((item for item in expanded if item == "PostgreSQL"), "the current database")
    return f"Choose {_expand_compact_atom(decision)} for {team}, {deadline}, and {store}, and keep the path to future decomposition open."


def _local_audit_review(finding: str, mitigation: list[str]) -> str:
    fix = _expand_compact_atom(mitigation[0]) if mitigation else "remove the unsafe path"
    return f"Treat {_expand_compact_atom(finding)} as a header auth risk, apply {fix}, and verify spoofed requests fail."


def _local_audit_refactor(target: str, constraints: list[str]) -> str:
    expanded = _expand_atoms(constraints, limit=2)
    core = ", ".join(expanded) if expanded else "behavioral invariants"
    return f"Refactor {_expand_compact_atom(target)} to async/await with minimal behavior change, preserve {core}, and verify the single next(err) path."


def _inflate_packed_payload(payload: list[Any], schema_name: str) -> dict[str, Any]:
    if schema_name == "debug_pack":
        return {
            "m": payload[0],
            "t": payload[1],
            "c": payload[2],
            "h": payload[3],
            "p": payload[4],
            "v": payload[5],
            "r": payload[6],
            "a": payload[7],
        }
    if schema_name == "review_pack":
        return {
            "m": payload[0],
            "f": payload[1],
            "e": payload[2],
            "p": payload[3],
            "v": payload[4],
            "r": payload[5],
            "a": payload[6],
        }
    if schema_name == "debug_slot_pack":
        return {
            "m": payload[0],
            "t": payload[1],
            "c": [item for item in str(payload[2]).split(";") if item],
            "h": payload[3],
            "p": [item for item in str(payload[4]).split(";") if item],
            "v": [item for item in str(payload[5]).split(";") if item],
            "r": [item for item in str(payload[6]).split(";") if item],
            "a": [item for item in str(payload[7]).split(";") if item],
        }
    if schema_name == "review_slot_pack":
        return {
            "m": payload[0],
            "f": payload[1],
            "e": payload[2],
            "p": [item for item in str(payload[3]).split(";") if item],
            "v": [item for item in str(payload[4]).split(";") if item],
            "r": [item for item in str(payload[5]).split(";") if item],
            "a": [item for item in str(payload[6]).split(";") if item],
        }
    raise KeyError(f"Unsupported packed schema: {schema_name}")


def _compact_or_quote(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return '""'
    if COMPACT_EXPR_RE.match(stripped):
        return stripped
    return json.dumps(stripped, ensure_ascii=False)


def _canonicalize_lite_payload(payload: dict[str, Any]) -> dict[str, Any]:
    canonical = dict(payload)
    for key, value in list(canonical.items()):
        if key == "m":
            continue
        if isinstance(value, str):
            canonical[key] = _compact_or_quote(value)
            continue
        if isinstance(value, list):
            canonical[key] = [_compact_or_quote(str(item)) for item in value]
    return canonical


def render_schema_payload(payload: dict[str, Any], schema_name: str | None = None) -> str:
    if isinstance(payload, dict) and schema_name in {"debug_pack", "review_pack", "debug_slot_pack", "review_slot_pack"} and "d" in payload and isinstance(payload["d"], list):
        payload = payload["d"]
    if isinstance(payload, list):
        if schema_name is None:
            raise KeyError("Packed payload requires schema_name")
        payload = _inflate_packed_payload(payload, schema_name)
    if isinstance(payload, dict) and schema_name in {"debug_wire_lite", "architecture_wire_lite", "review_wire_lite", "refactor_wire_lite"}:
        payload = _canonicalize_lite_payload(payload)
    mode = payload.get("mode") or payload.get("m")
    lines = [f"@flint v0 {mode}", *_render_codebook(payload.get("codebook", []))]

    if mode == "memory":
        for memory_expr in payload["memory"]:
            lines.append(f"M: {memory_expr}")
        return "\n".join(lines)

    if schema_name == "debug_hybrid":
        lines.append(f"G: fix({payload['target']})")
        lines.append(f"C: {_join(payload['constraints'], '∧')}")
        lines.append(f"H: {payload['cause']}")
        lines.append(f"P: {_join(payload['patch'], '→')}")
        lines.append(f"V: {_join(payload['tests'], '∧')}")
        lines.append(f"R: {_join(_risk_items(payload['risks']), '∧')}")
        lines.append(f"A: {_join(payload['answer'], '∧')}")
        lines.extend(["", "[AUDIT]", payload["audit"].strip()])
        return "\n".join(lines)

    if schema_name == "architecture_hybrid":
        lines.append(f"G: decide({payload['decision']})")
        lines.append(f"C: {_join(payload['constraints'], '∧')}")
        lines.append(f"H: {_join(payload['reasons'], '∧')} ⇒ prefer({payload['decision']})")
        lines.append(f"P: {_join(payload['plan'], '→')}")
        lines.append(f"R: {_join(_risk_items(payload['risks']), '∧')}")
        lines.append(f"A: {_join(payload['answer'], '∧')}")
        lines.extend(["", "[AUDIT]", payload["audit"].strip()])
        return "\n".join(lines)

    if schema_name == "review_hybrid":
        lines.append("G: review(patch)")
        lines.append(f"H: {payload['finding']} ⇒ {payload['exploit']}")
        lines.append(f"P: {_join(payload['mitigation'], '→')}")
        lines.append(f"V: {_join(payload['verification'], '∧')}")
        lines.append(f"R: {_join(_risk_items(payload['risks']), '∧')}")
        lines.append(f"A: {_join(payload['answer'], '∧')}")
        lines.extend(["", "[AUDIT]", payload["audit"].strip()])
        return "\n".join(lines)

    if schema_name == "refactor_hybrid":
        lines.append(f"G: refactor({payload['target']})")
        lines.append(f"C: {_join(payload['constraints'], '∧')}")
        lines.append(f"P: {_join(payload['transform'], '→')}")
        lines.append(f"V: {_join(payload['verification'], '∧')}")
        lines.append(f"R: {_join(_risk_items(payload['risks']), '∧')}")
        lines.append(f"A: {_join(payload['answer'], '∧')}")
        lines.extend(["", "[AUDIT]", payload["audit"].strip()])
        return "\n".join(lines)

    if schema_name in {"debug_wire", "debug_wire_lite"}:
        lines.append(f"G: fix({payload['t']})")
        lines.append(f"C: {_join(payload['c'], '∧')}")
        lines.append(f"H: {payload['h']}")
        lines.append(f"P: {_join(payload['p'], '→')}")
        lines.append(f"V: {_join(payload['v'], '∧')}")
        lines.append(f"R: {_join(_risk_items(payload['r']), '∧')}")
        lines.append(f"A: {_join(payload['a'], '∧')}")
        lines.extend(["", "[AUDIT]", _local_audit_debug(payload["t"], payload["c"], payload["v"])])
        return "\n".join(lines)

    if schema_name in {"architecture_wire", "architecture_wire_lite"}:
        lines.append(f"G: decide({payload['d']})")
        lines.append(f"C: {_join(payload['c'], '∧')}")
        lines.append(f"H: {_join(payload['h'], '∧')} ⇒ prefer({payload['d']})")
        lines.append(f"P: {_join(payload['p'], '→')}")
        lines.append(f"R: {_join(_risk_items(payload['r']), '∧')}")
        lines.append(f"A: {_join(payload['a'], '∧')}")
        lines.extend(["", "[AUDIT]", _local_audit_architecture(payload["d"], payload["c"])])
        return "\n".join(lines)

    if schema_name in {"review_wire", "review_wire_lite"}:
        lines.append("G: review(patch)")
        lines.append(f"H: {payload['f']} ⇒ {payload['e']}")
        lines.append(f"P: {_join(payload['p'], '→')}")
        lines.append(f"V: {_join(payload['v'], '∧')}")
        lines.append(f"R: {_join(_risk_items(payload['r']), '∧')}")
        lines.append(f"A: {_join(payload['a'], '∧')}")
        lines.extend(["", "[AUDIT]", _local_audit_review(payload["f"], payload["p"])])
        return "\n".join(lines)

    if schema_name in {"refactor_wire", "refactor_wire_lite"}:
        lines.append(f"G: refactor({payload['t']})")
        lines.append(f"C: {_join(payload['c'], '∧')}")
        lines.append(f"P: {_join(payload['p'], '→')}")
        lines.append(f"V: {_join(payload['v'], '∧')}")
        lines.append(f"R: {_join(_risk_items(payload['r']), '∧')}")
        lines.append(f"A: {_join(payload['a'], '∧')}")
        lines.extend(["", "[AUDIT]", _local_audit_refactor(payload["t"], payload["c"])])
        return "\n".join(lines)

    if schema_name in {"debug_pack", "debug_slot_pack"}:
        lines.append(f"G: fix({payload['t']})")
        lines.append(f"C: {_join(payload['c'], '∧')}")
        lines.append(f"H: {payload['h']}")
        lines.append(f"P: {_join(payload['p'], '→')}")
        lines.append(f"V: {_join(payload['v'], '∧')}")
        lines.append(f"R: {_join(_risk_items(payload['r']), '∧')}")
        lines.append(f"A: {_join(payload['a'], '∧')}")
        lines.extend(["", "[AUDIT]", _local_audit_debug(payload["t"], payload["c"], payload["v"])])
        return "\n".join(lines)

    if schema_name in {"review_pack", "review_slot_pack"}:
        lines.append("G: review(patch)")
        lines.append(f"H: {payload['f']} ⇒ {payload['e']}")
        lines.append(f"P: {_join(payload['p'], '→')}")
        lines.append(f"V: {_join(payload['v'], '∧')}")
        lines.append(f"R: {_join(_risk_items(payload['r']), '∧')}")
        lines.append(f"A: {_join(payload['a'], '∧')}")
        lines.extend(["", "[AUDIT]", _local_audit_review(payload["f"], payload["p"])])
        return "\n".join(lines)

    lines.append(f"G: {payload['goal']}")
    lines.append(f"C: {_join(payload['constraints'], '∧')}")
    if payload.get("has_hypothesis"):
        lines.append(f"H: {payload['hypothesis_left']} ⇒ {payload['hypothesis_right']}")
    lines.append(f"P: {_join(payload['plan'], '→')}")
    lines.append(f"V: {_join(payload['verification'], '∧')}")
    if payload.get("risks"):
        lines.append(f"R: {_join(_risk_items(payload['risks']), '∧')}")
    if payload.get("questions"):
        question_items = [item if item.endswith("?") else f"{item} ?" for item in payload["questions"]]
        lines.append(f"Q: {_join(question_items, '∧')}")
    lines.append(f"A: {_join(payload['answer'], '∧')}")
    audit = payload.get("audit", "").strip()
    if mode == "hybrid" or audit:
        lines.extend(["", "[AUDIT]", audit])
    return "\n".join(lines)
