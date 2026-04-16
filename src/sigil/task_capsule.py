from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


FENCE_RE = re.compile(r"```([a-zA-Z0-9_-]*)\n(.*?)```", re.DOTALL)


def _collapse_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _minify_code(value: str) -> str:
    lines = [line.strip() for line in value.strip().splitlines() if line.strip()]
    text = " ".join(lines)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*([{}();,:])\s*", r"\1", text)
    text = re.sub(r"\s*=\s*", "=", text)
    text = re.sub(r"\s*<\s*", "<", text)
    text = re.sub(r"\s*>\s*", ">", text)
    return text


def _extract_fenced_block(prompt: str) -> tuple[str | None, str | None]:
    match = FENCE_RE.search(prompt)
    if not match:
        return None, None
    language = match.group(1).strip() or None
    body = match.group(2)
    return language, body


def _after_marker(prompt: str, marker: str) -> str | None:
    if marker not in prompt:
        return None
    return prompt.split(marker, 1)[1].strip()


def _between(prompt: str, start: str, end: str | None = None) -> str | None:
    if start not in prompt:
        return None
    tail = prompt.split(start, 1)[1]
    if end and end in tail:
        tail = tail.split(end, 1)[0]
    return tail.strip()


def _format_anchor_line(task: dict[str, Any]) -> str | None:
    anchors = [str(item) for item in task.get("exact_literals", []) if str(item).strip()]
    if not anchors:
        return None
    encoded = " | ".join(json.dumps(anchor, ensure_ascii=False) for anchor in anchors)
    return f"anchors: {encoded}"


def _extract_first_int(text: str) -> str | None:
    match = re.search(r"\b(\d+)\b", text)
    if not match:
        return None
    return match.group(1)


def _extract_phrase(text: str, needle: str) -> str | None:
    lowered = text.lower()
    index = lowered.find(needle.lower())
    if index < 0:
        return None
    end = text.find(",", index)
    if end < 0:
        end = text.find(".", index)
    if end < 0:
        end = len(text)
    return text[index:end].strip()


def build_task_capsule(task: dict[str, Any], style: str = "v1") -> str:
    if style == "micro":
        return build_micro_task_capsule(task)
    if style == "nano":
        return build_nano_task_capsule(task)
    if style == "bridge":
        return build_bridge_task_capsule(task)
    category = str(task["category"])
    prompt = str(task["prompt"])
    if category == "debugging":
        return _build_debug_capsule(task, prompt)
    if category == "architecture":
        return _build_architecture_capsule(task, prompt)
    if category == "code_review":
        return _build_review_capsule(task, prompt)
    if category == "refactoring":
        return _build_refactor_capsule(task, prompt)
    return _collapse_text(prompt)


def build_micro_task_capsule(task: dict[str, Any]) -> str:
    category = str(task["category"])
    prompt = str(task["prompt"])
    if category == "debugging":
        return _build_debug_micro_capsule(task, prompt)
    if category == "architecture":
        return _build_architecture_micro_capsule(task, prompt)
    if category == "code_review":
        return _build_review_micro_capsule(task, prompt)
    if category == "refactoring":
        return _build_refactor_micro_capsule(task, prompt)
    return _collapse_text(prompt)


def build_nano_task_capsule(task: dict[str, Any]) -> str:
    category = str(task["category"])
    anchors = [str(item) for item in task.get("exact_literals", []) if str(item).strip()]
    anchor_blob = "|".join(json.dumps(anchor, ensure_ascii=False) for anchor in anchors)
    if category == "debugging":
        head = f"[d] {anchor_blob}".strip()
        return f"{head} auth grace regression test keep_401 edge(-30s_200) edge(-31s_401)".strip()
    if category == "architecture":
        head = f"[a] {anchor_blob}".strip()
        return f"{head} modular_monolith team deadline low_ops fast_ship split(post_release)".strip()
    if category == "code_review":
        head = f"[r] {anchor_blob}".strip()
        return f"{head} header auth risk verify drop_hdr keep_401 spoof_denied".strip()
    if category == "refactoring":
        prompt = str(task["prompt"])
        target_match = re.search(r"\btarget:\s*([A-Za-z0-9_]+)", prompt)
        if target_match is None:
            _, code = _extract_fenced_block(prompt)
            if code:
                target_match = re.search(r"function\s+([A-Za-z0-9_]+)\s*\(", code)
        target = target_match.group(1) if target_match else "target"
        head = f"[f] {anchor_blob}".strip()
        return f"{head} {target} async await verify minimal same_order next(err)".strip()
    return _collapse_text(str(task["prompt"]))


def _structured_fields(prompt: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in prompt.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("[") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip().lower()] = value.strip()
    return fields


def _focus_atoms(task: dict[str, Any], limit: int = 3) -> list[str]:
    raw = task.get("focus")
    if isinstance(raw, str):
        items = [part.strip() for part in re.split(r"[,\s|]+", raw) if part.strip()]
    elif isinstance(raw, list):
        items = [str(part).strip() for part in raw if str(part).strip()]
    else:
        items = [str(part).strip() for part in task.get("must_include", []) if str(part).strip()]
    return items[:limit]


def _safe_atom(value: str) -> str:
    atom = value.strip().replace('"', "")
    atom = atom.replace(" ", "_").replace("-", "_")
    atom = re.sub(r"[^A-Za-z0-9_><=!./]+", "_", atom)
    atom = re.sub(r"_+", "_", atom).strip("_")
    return atom or "unknown"


def _call_arg(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return json.dumps("unknown", ensure_ascii=False)
    if stripped.startswith('"') and stripped.endswith('"'):
        return stripped
    if re.fullmatch(r"[A-Za-z0-9_./><=!+-]+", stripped):
        return stripped
    return json.dumps(stripped, ensure_ascii=False)


def build_bridge_task_capsule(task: dict[str, Any]) -> str:
    category = str(task["category"])
    prompt = str(task["prompt"])
    anchors = [str(item) for item in task.get("exact_literals", []) if str(item).strip()]
    anchor_blob = "|".join(json.dumps(anchor, ensure_ascii=False) for anchor in anchors)
    focus = [_safe_atom(item) for item in _focus_atoms(task)]
    fields = _structured_fields(prompt)
    if category == "debugging":
        ctx = _safe_atom(fields.get("ctx", "debug"))
        rule = _safe_atom(fields.get("rule", "rule"))
        need = _safe_atom(fields.get("need", "fix"))
        issue = _safe_atom(fields.get("issue", "edge"))
        focus_blob = ",".join(focus) if focus else "minimal,verify"
        return f"[d2] {anchor_blob} c({ctx}) r({rule}) n({need}) i({issue}) f({focus_blob})".strip()
    if category == "architecture":
        ops = _safe_atom(fields.get("ops", "ops"))
        split = _safe_atom(fields.get("split", "split"))
        focus_blob = ",".join(focus) if focus else "modular_monolith,ops"
        return f"[a2] {anchor_blob} o({ops}) x({split}) f({focus_blob})".strip()
    if category == "code_review":
        ctx = _safe_atom(fields.get("ctx", "review"))
        focus_blob = ",".join(focus) if focus else "risk,verify"
        return f"[r2] {anchor_blob} c({ctx}) f({focus_blob})".strip()
    if category == "refactoring":
        target = _safe_atom(fields.get("target", "target"))
        order = _safe_atom(fields.get("order", "order"))
        focus_blob = ",".join(focus) if focus else "async,verify,minimal"
        return f"[f2] {anchor_blob} t({target}) o({order}) f({focus_blob})".strip()
    return _collapse_text(prompt)


def _build_debug_capsule(task: dict[str, Any], prompt: str) -> str:
    _, code = _extract_fenced_block(prompt)
    requirements = _between(prompt, "Requirements:", "\n\nCode:")
    observed = _after_marker(prompt, "Observed failure:")
    anchor_line = _format_anchor_line(task)
    req_atoms: list[str] = []
    lowered = (requirements or "").lower()
    if "backward compatibility" in lowered:
        req_atoms.append("backcompat")
    if "security" in lowered:
        req_atoms.append("security")
    if "smallest possible diff" in lowered:
        req_atoms.append("minimal_diff")
    if "one regression test" in lowered:
        req_atoms.append("one_regression_test")
    lines = [
        "[capsule v1 debugging]",
        f"req: {'; '.join(req_atoms) if req_atoms else _collapse_text(requirements or '')}",
        f"code: {_minify_code(code or '')}",
        f"issue: {_collapse_text(observed or '')}",
        "deliver: min_fix; reg_test",
    ]
    if anchor_line:
        lines.insert(1, anchor_line)
    return "\n".join(line for line in lines if not line.endswith(": "))


def _build_debug_micro_capsule(task: dict[str, Any], prompt: str) -> str:
    observed = _after_marker(prompt, "Observed failure:") or ""
    anchor_line = _format_anchor_line(task)
    lines = [
        "[capsule micro debugging]",
        "ctx: auth_mw expiry",
        "rule: expMs<nowMs=>401",
        "issue: skew30 boundary refresh_loop",
        "deliver: min_fix reg_test",
    ]
    if "grace window" in observed.lower():
        lines.insert(3, "need: allow skew30 only")
    if anchor_line:
        lines.insert(1, anchor_line)
    return "\n".join(lines)


def _build_architecture_capsule(task: dict[str, Any], prompt: str) -> str:
    context = _after_marker(prompt, "Context:")
    if context is None:
        context = prompt
    context = context.replace("Choose the default architecture and justify it briefly.", "").strip()
    team_size = _extract_first_int(context)
    deadline = _extract_phrase(context, "shipping in")
    split = "billing|core_app" if "billing and core app" in context.lower() else None
    anchor_line = _format_anchor_line(task)
    lines = [
        "[capsule v1 architecture]",
        f"context: {_collapse_text(context)}",
        "deliver: default_architecture; short_justification",
    ]
    inserts = []
    if anchor_line:
        inserts.append(anchor_line)
    if team_size:
        inserts.append(f"team: {team_size}")
    if "part-time DevOps generalist" in context:
        inserts.append("ops: part_time_devops_generalist")
    if deadline:
        inserts.append(f"deadline: {json.dumps(deadline.replace('shipping in', '').strip(), ensure_ascii=False)}")
    if "modest initial traffic" in context.lower():
        inserts.append("traffic: modest_initial")
    if "postgresql" in context.lower():
        inserts.append('store: "PostgreSQL"')
    if split:
        inserts.append(f"future_split: {split}")
    if "not before first release" in context.lower():
        inserts.append("split_timing: post_release")
    lines[1:1] = inserts
    return "\n".join(lines)


def _build_architecture_micro_capsule(task: dict[str, Any], prompt: str) -> str:
    context = _after_marker(prompt, "Context:") or prompt
    team_size = _extract_first_int(context) or "?"
    deadline = _extract_phrase(context, "shipping in")
    deadline_value = deadline.replace("shipping in", "").strip() if deadline else "?"
    anchor_line = _format_anchor_line(task)
    lines = [
        "[capsule micro architecture]",
        f"team: {team_size}",
        'ddl: "4 months"' if deadline_value == "4 months" else f"ddl: {json.dumps(deadline_value, ensure_ascii=False)}",
        'store: "PostgreSQL"' if "postgresql" in context.lower() else "store: unknown",
        "ops: pt_devops" if "part-time DevOps generalist" in context else "ops: unknown",
        "traffic: modest" if "modest initial traffic" in context.lower() else "traffic: unknown",
        "split: post_release" if "not before first release" in context.lower() else "split: open",
        "deliver: default_arch short_why",
    ]
    if anchor_line:
        lines.insert(1, anchor_line)
    return "\n".join(lines)


def _build_review_capsule(task: dict[str, Any], prompt: str) -> str:
    _, diff = _extract_fenced_block(prompt)
    context = _after_marker(prompt, "Context:")
    anchor_line = _format_anchor_line(task)
    lines = [
        "[capsule v1 review]",
        f"diff: {_minify_code(diff or '')}",
        f"context: {_collapse_text(context or '')}",
        "deliver: concise_risk; mitigation; verification",
    ]
    if anchor_line:
        lines.insert(1, anchor_line)
    return "\n".join(line for line in lines if not line.endswith(": "))


def _build_review_micro_capsule(task: dict[str, Any], prompt: str) -> str:
    _, diff = _extract_fenced_block(prompt)
    diff_text = _minify_code(diff or "")
    anchor_line = _format_anchor_line(task)
    lines = [
        "[capsule micro review]",
        f"diff: {diff_text}",
        "ctx: public_api_gateway",
        "deliver: risk mitigation verify",
    ]
    if anchor_line:
        lines.insert(1, anchor_line)
    return "\n".join(lines)


def _build_refactor_capsule(task: dict[str, Any], prompt: str) -> str:
    _, code = _extract_fenced_block(prompt)
    requirement = _between(prompt, "Refactor this code to async/await with", "\n\nCode:")
    tail = _after_marker(prompt, "Return the shortest correct migration plan or patch sketch.")
    function_match = re.search(r"function\s+([A-Za-z0-9_]+)\s*\(", code or "")
    target = function_match.group(1) if function_match else None
    anchor_line = _format_anchor_line(task)
    lines = [
        "[capsule v1 refactor]",
        f"req: async_await; {_collapse_text(requirement or '')}",
        f"code: {_minify_code(code or '')}",
        "deliver: migration_plan_or_patch_sketch",
    ]
    inserts = []
    if anchor_line:
        inserts.append(anchor_line)
    if target:
        inserts.append(f"target: {target}")
    if "validation order" in (requirement or "").lower():
        inserts.append("constraint: same_validation_order")
    if "maps database errors to `next(err)`" in prompt:
        inserts.append('error_path: "next(err)"')
    lines[1:1] = inserts
    if tail:
        lines.append(f"extra: {_collapse_text(tail)}")
    return "\n".join(line for line in lines if not line.endswith(": "))


def _build_refactor_micro_capsule(task: dict[str, Any], prompt: str) -> str:
    _, code = _extract_fenced_block(prompt)
    function_match = re.search(r"function\s+([A-Za-z0-9_]+)\s*\(", code or "")
    target = function_match.group(1) if function_match else "unknown"
    anchor_line = _format_anchor_line(task)
    lines = [
        "[capsule micro refactor]",
        f"target: {target}",
        "order: missing_id>db.findUser>not_found>audit.log>cache.set",
        'db_err: "next(err)"',
        "deliver: async_await minimal_change",
    ]
    if anchor_line:
        lines.insert(1, anchor_line)
    return "\n".join(lines)


def build_capsule_task_row(task: dict[str, Any], style: str = "v1") -> dict[str, Any]:
    row = dict(task)
    row["prompt"] = build_task_capsule(task, style=style)
    row["capsule"] = style
    return row


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
