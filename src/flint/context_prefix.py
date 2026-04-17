from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .metrics import approx_token_count

HEADING_RE = re.compile(r"^[A-Z][A-Za-z /-]+:$")

SECTION_ORDER = (
    "product snapshot",
    "operational posture",
    "code and review conventions",
    "authentication and session rules",
    "token and expiry rules",
    "security review heuristics",
    "architecture heuristics",
    "refactor heuristics",
    "testing heuristics",
    "answer-style heuristics",
    "domain glossary",
    "repository norms",
    "what not to do",
    "what a strong answer usually contains",
)

LABELS = {
    "product snapshot": "core",
    "operational posture": "ops",
    "code and review conventions": "code",
    "authentication and session rules": "auth",
    "token and expiry rules": "expiry",
    "security review heuristics": "review",
    "architecture heuristics": "arch",
    "refactor heuristics": "refactor",
    "testing heuristics": "test",
    "answer-style heuristics": "style",
    "domain glossary": "glossary",
    "repository norms": "norms",
    "what not to do": "avoid",
    "what a strong answer usually contains": "answer",
}

FOCUSED_SECTIONS = {
    "debugging": (
        "product snapshot",
        "operational posture",
        "code and review conventions",
        "authentication and session rules",
        "token and expiry rules",
        "testing heuristics",
        "answer-style heuristics",
        "repository norms",
        "what not to do",
        "what a strong answer usually contains",
    ),
    "architecture": (
        "product snapshot",
        "operational posture",
        "architecture heuristics",
        "answer-style heuristics",
        "repository norms",
        "what not to do",
        "what a strong answer usually contains",
    ),
    "code_review": (
        "product snapshot",
        "operational posture",
        "code and review conventions",
        "authentication and session rules",
        "security review heuristics",
        "testing heuristics",
        "answer-style heuristics",
        "repository norms",
        "what not to do",
        "what a strong answer usually contains",
    ),
    "refactoring": (
        "product snapshot",
        "operational posture",
        "code and review conventions",
        "refactor heuristics",
        "testing heuristics",
        "answer-style heuristics",
        "repository norms",
        "what not to do",
        "what a strong answer usually contains",
    ),
}

NEEDLE_SECTIONS = {
    "debugging": (
        "authentication and session rules",
        "token and expiry rules",
        "testing heuristics",
        "code and review conventions",
        "repository norms",
    ),
    "architecture": (
        "architecture heuristics",
        "operational posture",
        "answer-style heuristics",
        "repository norms",
    ),
    "code_review": (
        "authentication and session rules",
        "security review heuristics",
        "testing heuristics",
        "repository norms",
    ),
    "refactoring": (
        "refactor heuristics",
        "code and review conventions",
        "testing heuristics",
        "repository norms",
    ),
}

DELTA_SECTIONS = {
    "debugging": (
        "authentication and session rules",
        "token and expiry rules",
        "testing heuristics",
    ),
    "architecture": (
        "architecture heuristics",
        "operational posture",
    ),
    "code_review": (
        "security review heuristics",
        "authentication and session rules",
    ),
    "refactoring": (
        "refactor heuristics",
        "testing heuristics",
    ),
}

PHRASE_REPLACEMENTS = (
    ("public API gateway", "public_gateway"),
    ("Node.js and TypeScript", "Node.js+TypeScript"),
    ("modular monolith", "modular_monolith"),
    ("part-time DevOps generalist", "pt_devops_generalist"),
    ("single error mapping", "single_error_mapping"),
    ("split readiness", "split_readiness"),
    ("trust boundary", "trust_boundary"),
    ("spoofed header", "spoofed_header"),
    ("clock drift", "clock_drift"),
    ("grace window", "grace_window"),
    ("horizontal privilege escalation", "horizontal_privilege_escalation"),
    ("backward compatibility", "backcompat"),
    ("regression risk", "regression_risk"),
    ("system of record", "SoR"),
    ("future split readiness", "future_split_readiness"),
    ("minimal-diff", "minimal_diff"),
    ("small composable helpers", "small_helpers"),
)

LEAD_REPLACEMENTS = (
    ("The team ", ""),
    ("Any flow where ", ""),
    ("Good mitigations are usually actions like ", "mitigate: "),
    ("Prefer ", ""),
    ("Do not ", "Avoid "),
    ("For ", ""),
    ("If ", "when "),
)

TRAIL_REPLACEMENTS = (
    (" is suspicious.", " suspicious."),
    (" is presumptively unsafe.", " unsafe."),
    (" is the default system of record.", " default SoR."),
    (" is the primary authentication mechanism for first-party clients.", " primary auth for first-party clients."),
    (" should ", " "),
)


def _collapse(value: str) -> str:
    text = re.sub(r"\s+", " ", value.strip())
    for old, new in PHRASE_REPLACEMENTS:
        text = text.replace(old, new)
    for old, new in LEAD_REPLACEMENTS:
        if text.startswith(old):
            text = new + text[len(old) :]
    for old, new in TRAIL_REPLACEMENTS:
        text = text.replace(old, new)
    text = text.replace(" > ", ">")
    text = text.replace(" - ", "; ")
    text = text.replace(" or ", " / ")
    return text.strip(" ;")


def parse_handbook_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"preamble": []}
    current = "preamble"
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if HEADING_RE.match(line):
            current = line[:-1].strip().lower()
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def _render_section(items: list[str], *, label: str, tight: bool) -> str | None:
    normalized: list[str] = []
    for item in items:
        text = item[2:].strip() if item.startswith("- ") else item
        text = _collapse(text)
        if tight:
            text = text.replace(" and ", " & ")
        normalized.append(text)
    if not normalized:
        return None
    separator = "; " if tight else " | "
    return f"{label}: {separator.join(normalized)}"


def _section_keys_for(category: str, style: str) -> tuple[str, ...]:
    if style == "focused":
        return FOCUSED_SECTIONS.get(category, SECTION_ORDER)
    return SECTION_ORDER


def _match_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _extract_task_terms(task: dict[str, Any] | None) -> tuple[list[str], set[str]]:
    if not task:
        return [], set()
    anchors = [str(item).strip() for item in task.get("exact_literals", []) if str(item).strip()]
    raw_values: list[str] = anchors[:]
    raw_values.extend(str(item).strip() for item in task.get("must_include", []) if str(item).strip())
    raw_values.extend(str(item).strip() for item in task.get("focus", []) if str(item).strip())
    prompt = str(task.get("prompt") or "")
    raw_values.extend(match.group(0) for match in re.finditer(r"`([^`]+)`", prompt))
    terms: set[str] = set()
    for value in raw_values:
        parts = _match_text(value).split()
        for part in parts:
            if len(part) >= 3:
                terms.add(part)
    return anchors, terms


def _score_item(item: str, *, anchors: list[str], terms: set[str]) -> int:
    lowered = item.lower()
    score = 0
    for anchor in anchors:
        if anchor and anchor.lower() in lowered:
            score += 4
    match_text = _match_text(item)
    words = set(match_text.split())
    score += sum(1 for term in terms if term in words)
    return score


def _select_targeted_items(
    section_name: str,
    items: list[str],
    *,
    anchors: list[str],
    terms: set[str],
) -> list[str]:
    if not items:
        return []
    scored = [(_score_item(item, anchors=anchors, terms=terms), item) for item in items]
    scored.sort(key=lambda pair: (pair[0], len(pair[1])), reverse=True)
    selected = [item for score, item in scored if score > 0]
    if section_name in {"repository norms", "domain glossary"}:
        return selected[:2]
    if section_name in {"answer-style heuristics", "what not to do", "what a strong answer usually contains"}:
        return selected[:2] or items[:1]
    if section_name in {"product snapshot", "operational posture"}:
        return selected[:2] or items[:2]
    if section_name in {"authentication and session rules", "token and expiry rules", "security review heuristics", "architecture heuristics", "refactor heuristics", "testing heuristics"}:
        return selected[:3] or items[:1]
    if section_name in {"code and review conventions"}:
        return selected[:2] or items[:1]
    return selected[:2] or items[:1]


def _render_targeted_section(
    section_name: str,
    items: list[str],
    *,
    anchors: list[str],
    terms: set[str],
) -> str | None:
    selected = _select_targeted_items(section_name, items, anchors=anchors, terms=terms)
    return _render_section(selected, label=LABELS.get(section_name, section_name), tight=True)


def _render_needle_section(
    section_name: str,
    items: list[str],
    *,
    anchors: list[str],
    terms: set[str],
) -> str | None:
    selected = _select_targeted_items(section_name, items, anchors=anchors, terms=terms)
    if not selected:
        return None
    limit = 2 if section_name == "repository norms" else 1
    return _render_section(selected[:limit], label=LABELS.get(section_name, section_name), tight=True)


def _render_delta_section(
    section_name: str,
    items: list[str],
    *,
    anchors: list[str],
    terms: set[str],
) -> str | None:
    selected = _select_targeted_items(section_name, items, anchors=anchors, terms=terms)
    if not selected:
        return None
    return _render_section(selected[:1], label=LABELS.get(section_name, section_name), tight=True)


def compile_context_prefix(
    text: str,
    *,
    category: str,
    style: str = "cacheable",
    task: dict[str, Any] | None = None,
) -> str:
    if style not in {"cacheable", "focused", "targeted", "needle", "delta"}:
        raise ValueError(f"Unsupported context style: {style}")
    sections = parse_handbook_sections(text)
    preamble = [_collapse(item) for item in sections.get("preamble", []) if item.strip()]
    title = preamble[0] if preamble else "Project handbook"
    intro = preamble[1] if len(preamble) > 1 else "Shared durable project context."
    anchors, terms = _extract_task_terms(task)
    if style == "delta":
        lines = [f"[ctx {style} {category}]"]
    else:
        lines = [
            f"[ctx {style} {category}]",
            f"title: {title}",
            f"scope: {intro}",
            f"focus: {category}",
        ]
    if style in {"targeted", "needle", "delta"} and anchors:
        encoded = " | ".join(f'"{anchor}"' for anchor in anchors[:4])
        lines.append(f"anchors: {encoded}")
    tight = style in {"focused", "targeted", "needle", "delta"}
    if style == "needle":
        keys = NEEDLE_SECTIONS.get(category, FOCUSED_SECTIONS.get(category, SECTION_ORDER[:4]))
    elif style == "delta":
        keys = DELTA_SECTIONS.get(category, NEEDLE_SECTIONS.get(category, SECTION_ORDER[:2]))
    else:
        keys = _section_keys_for(category, "focused" if style in {"targeted", "needle", "delta"} else style)
    for key in keys:
        if style == "targeted":
            rendered = _render_targeted_section(key, sections.get(key, []), anchors=anchors, terms=terms)
        elif style == "needle":
            rendered = _render_needle_section(key, sections.get(key, []), anchors=anchors, terms=terms)
        elif style == "delta":
            rendered = _render_delta_section(key, sections.get(key, []), anchors=anchors, terms=terms)
        else:
            rendered = _render_section(sections.get(key, []), label=LABELS.get(key, key), tight=tight)
        if rendered:
            lines.append(rendered)

    rendered = "\n".join(lines)
    if style == "cacheable":
        token_count = approx_token_count(rendered)
        if token_count < 680:
            glossary = sections.get("domain glossary", [])
            norms = sections.get("repository norms", [])
            for extra in (glossary, norms, glossary):
                extra_line = _render_section(extra, label="cache_fill", tight=False)
                if extra_line:
                    lines.append(extra_line)
                rendered = "\n".join(lines)
                if approx_token_count(rendered) >= 680:
                    break
    if style == "targeted":
        token_count = approx_token_count(rendered)
        if token_count > 340:
            compact_lines = lines[:5]
            for key in keys:
                rendered = _render_targeted_section(key, sections.get(key, []), anchors=anchors, terms=terms)
                if rendered:
                    label = rendered.split(":", 1)[0]
                    if label in {"core", "ops", "auth", "expiry", "review", "arch", "refactor", "test", "glossary", "norms"}:
                        compact_lines.append(rendered)
                    if approx_token_count("\n".join(compact_lines)) >= 300:
                        break
            lines = compact_lines
    if style == "needle":
        token_count = approx_token_count(rendered)
        if token_count > 180:
            compact_lines = lines[:5]
            for key in keys:
                section_line = _render_needle_section(key, sections.get(key, []), anchors=anchors, terms=terms)
                if section_line:
                    compact_lines.append(section_line)
                if approx_token_count("\n".join(compact_lines)) >= 150:
                    break
            lines = compact_lines
    if style == "delta":
        token_count = approx_token_count(rendered)
        anchor_line_count = 2 if anchors else 1
        if token_count > 120:
            compact_lines = lines[:anchor_line_count]
            for key in keys:
                section_line = _render_delta_section(key, sections.get(key, []), anchors=anchors, terms=terms)
                if section_line:
                    compact_lines.append(section_line)
                if approx_token_count("\n".join(compact_lines)) >= 100:
                    break
            lines = compact_lines
    return "\n".join(lines)


def compile_context_layers(
    text: str,
    *,
    category: str,
    task: dict[str, Any] | None = None,
    shared_style: str = "cacheable",
    task_style: str = "targeted",
) -> tuple[str, str]:
    shared_prefix = compile_context_prefix(text, category="shared", style=shared_style)
    task_context = compile_context_prefix(text, category=category, style=task_style, task=task)
    return shared_prefix, task_context


def load_context_prefix(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()
