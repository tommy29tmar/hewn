from __future__ import annotations

import re
from pathlib import Path

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


def compile_context_prefix(text: str, *, category: str, style: str = "cacheable") -> str:
    if style not in {"cacheable", "focused"}:
        raise ValueError(f"Unsupported context style: {style}")
    sections = parse_handbook_sections(text)
    preamble = [_collapse(item) for item in sections.get("preamble", []) if item.strip()]
    title = preamble[0] if preamble else "Project handbook"
    intro = preamble[1] if len(preamble) > 1 else "Shared durable project context."
    lines = [
        f"[ctx {style} {category}]",
        f"title: {title}",
        f"scope: {intro}",
        f"focus: {category}",
    ]
    tight = style == "focused"
    for key in _section_keys_for(category, style):
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
    return "\n".join(lines)


def load_context_prefix(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()
