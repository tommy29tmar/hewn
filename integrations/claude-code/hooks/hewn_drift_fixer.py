#!/usr/bin/env python3
"""Hewn drift-fix hook — UserPromptSubmit classifier.

Reads a Claude Code UserPromptSubmit event from stdin, classifies the
turn as IR-shape or prose-shape using a score-based rule set, and emits
a hookSpecificOutput JSON that reasserts the Hewn routing directive
as additionalContext. This pins the model's attention to the task
shape on every turn, preventing the T2+ drift observed when relying
on the system prompt alone.

Pure Python, no external deps. Runs in <10ms.

Score-based classifier:
- Positive signals pull toward IR (structural, analytical, debugging).
- Negative signals pull toward prose (writing, explanation, leadership).
- Findings signals pull toward compact diagnostic lists instead of IR.
- Threshold >= 2 -> IR, otherwise prose.

Locales:
- Rule sets live in hooks/locales/<name>.py (en.py, it.py, es.py, fr.py, de.py).
- Resolution precedence (highest first):
    1. HEWN_LOCALE env var (e.g. "en,it") — explicit override.
    2. $LC_ALL / $LC_MESSAGES / $LANG auto-detect. If the 2-letter prefix
       matches a shipped locale file, stack it on top of English.
       Example: LANG=it_IT.UTF-8 -> loads en + it.
    3. English only. Applies when auto-detect hits C/POSIX/en_*/unshipped.
- Common overrides:
    HEWN_LOCALE=en       # force English-only despite a non-English shell
    HEWN_LOCALE=en,it    # English + Italian
    HEWN_LOCALE=en,es,fr # English + Spanish + French

See tests/test_hewn_drift_fixer.py for the classification corpus.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path


LOCALE_DIR = Path(__file__).resolve().parent / "locales"
IR_THRESHOLD = 2


def _load_locale(name: str):
    path = LOCALE_DIR / f"{name}.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"hewn_locale_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_RULES_CACHE: dict[tuple[str, ...], tuple] = {}


def _assemble_rules(locales: tuple[str, ...]) -> tuple:
    if locales in _RULES_CACHE:
        return _RULES_CACHE[locales]
    ir_rules: list[tuple[str, int]] = []
    prose_rules: list[tuple[str, int]] = []
    findings_rules: list[str] = []
    code_artifact_rules: list[str] = []
    polished_audience_rules: list[str] = []
    for name in locales:
        mod = _load_locale(name)
        if mod is None:
            continue
        ir_rules.extend(getattr(mod, "IR_RULES", []))
        prose_rules.extend(getattr(mod, "PROSE_RULES", []))
        findings_rules.extend(getattr(mod, "FINDINGS_RULES", []))
        code_artifact_rules.extend(getattr(mod, "CODE_ARTIFACT_RULES", []))
        polished_audience_rules.extend(getattr(mod, "POLISHED_AUDIENCE_RULES", []))
    result = (ir_rules, prose_rules, findings_rules, code_artifact_rules, polished_audience_rules)
    _RULES_CACHE[locales] = result
    return result


def _detect_system_locale() -> str | None:
    """Return a 2-letter locale code from LC_ALL/LC_MESSAGES/LANG if a
    matching locale file ships with this install. Returns None when the
    system locale is unset, POSIX/C, English, or a language we don't ship.
    """
    for env_var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(env_var, "")
        if not val or val in ("C", "POSIX", "C.UTF-8"):
            continue
        prefix = val.split("_", 1)[0].split(".", 1)[0].lower()
        if not prefix or prefix == "en":
            return None
        if (LOCALE_DIR / f"{prefix}.py").exists():
            return prefix
        return None
    return None


def _default_locales() -> tuple[str, ...]:
    """Resolve locale stack. Precedence: HEWN_LOCALE > $LANG auto-detect > en-only."""
    raw = os.environ.get("HEWN_LOCALE")
    if raw:
        parts = tuple(s.strip() for s in raw.split(",") if s.strip())
        return parts or ("en",)
    detected = _detect_system_locale()
    if detected:
        return ("en", detected)
    return ("en",)


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, re.IGNORECASE | re.MULTILINE) for p in patterns)


def classify(prompt: str, locales: tuple[str, ...] | None = None) -> str:
    """Return one of 'ir' | 'prose_code' | 'prose_findings' | 'prose_polished_code' | 'prose_polished' | 'prose_caveman'.

    Decision order (first match wins):
      1. Polished audience AND code artifact requested -> 'prose_polished_code'.
      2. Strongly polished audience (no code) -> 'prose_polished'.
      3. Code artifact requested (no polished audience) -> 'prose_code'.
      4. Ranked/listed independent findings -> 'prose_findings'.
      5. Technical score >= IR_THRESHOLD -> 'ir'.
      6. Any polished-audience hint -> 'prose_polished'.
      7. Default -> 'prose_caveman' (terse, compressed prose).
    """
    text = prompt or ""
    if locales is None:
        locales = _default_locales()
    ir_rules, prose_rules, findings_rules, code_artifact_rules, polished_audience_rules = _assemble_rules(locales)

    ir_score = 0
    prose_score = 0
    for pattern, weight in ir_rules:
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            ir_score += weight
    for pattern, weight in prose_rules:
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            prose_score += weight

    wants_code = _matches_any(text, code_artifact_rules)
    polished_audience = _matches_any(text, polished_audience_rules)
    wants_findings = _matches_any(text, findings_rules)

    if polished_audience and prose_score >= 4 and wants_code:
        return "prose_polished_code"
    if polished_audience and prose_score >= 4:
        return "prose_polished"
    if wants_code:
        return "prose_code"
    if wants_findings:
        return "prose_findings"
    if ir_score - prose_score >= IR_THRESHOLD:
        return "ir"
    if polished_audience:
        return "prose_polished"
    return "prose_caveman"


IR_DIRECTIVE = (
    "[TURN CLASSIFICATION: IR-shape] This turn has a crisp technical goal "
    "and verifiable endpoint. Respond in Hewn IR: emit '@hewn v0 hybrid' "
    "+ G/C/P/V/A clauses as free text. Exactly 6 lines, no prose, no fences, "
    "no audit, no blank lines. Never emit H:, R:, Q:, @cb, or [AUDIT]. "
    "Never join atoms with commas; use ∧ only when multiple atoms are needed. "
    "Stop after A:. Do NOT respond in prose for this turn. "
    "Atoms must be lowercase_snake_case identifiers, call form f(\"x\"), or "
    "quoted literals. Unquoted atoms may contain only a-z, 0-9, underscore. "
    "Never use = + - < > == != && || [] {} . comma or spaces inside an "
    "unquoted atom. Literal user values always go in quotes. NEVER use suffix "
    "form like evaluates_to_\"6\" or fix_expected_to_\"7\" (underscore "
    "immediately before a quote) — use call form evaluates_to(\"6\") or rename "
    "the concept (evaluates_to_six). No nested parens, multi-arg calls, or "
    "code blocks inside atoms. For brief technical "
    "Q&A prompts (explain/how/why/difference/when should I use), emit "
    "micro-IR: exactly 1 short atom per G/C/P/V/A clause; no ∧ joins in "
    "micro-IR; if comparison needs two sides, encode contrast inside one "
    "atom; atoms 1-2 semantic words in snake_case; use shortest clear atom; "
    "prefer standard abbreviations (db, req, res, cfg, fn); do not prefix G "
    "with explain_; no examples, caveats, implementation lists, or extra "
    "facts unless user asks. Example shape: @hewn v0 hybrid / G: db_pool / "
    "C: open_conn_cost / P: checkout_return / V: lower_latency / "
    "A: tune_size. Debounce shape: G: debounce / C: keyspam / "
    "P: wait_idle / V: fewer_req / A: set_ms."
)

PROSE_CODE_DIRECTIVE = (
    "[TURN CLASSIFICATION: prose+code] This turn asks for an executable "
    "artifact (fix, test, updated file, snippet). Respond with a brief "
    "Caveman-compressed prose analysis (2-4 lines) followed by one or "
    "more fenced code blocks (```lang ... ```). Do NOT emit Hewn IR "
    "atoms — code must render verbatim. Keep the analysis terse: drop "
    "articles, no filler. Code block first when the user asked to 'show' it."
)

PROSE_CAVEMAN_DIRECTIVE = (
    "MICRO_PROSE_MODE. Answer plain prose only. 1-3 short natural-language "
    "lines. No labels, headers, bullets, tables, or checklists unless user "
    "asks. If context missing, ask only needed input. Preserve exact errors. "
    "Ignore current repo/cwd/language unless user explicitly says it is target."
)

PROSE_FINDINGS_DIRECTIVE = (
    "[TURN CLASSIFICATION: prose-findings] This turn asks for a ranked "
    "or enumerated set of independent diagnostic findings (bugs, risks, "
    "issues, vulnerabilities, blockers, footguns, failure modes). Do NOT "
    "emit Hewn IR. Use tools when facts about "
    "actual code/files/repo state are needed. Respond with a compact "
    "numbered findings list only: no intro, no closing summary, no "
    "markdown headers, no bold. Preserve requested count/order. Each "
    "item should include title, file:line or evidence, trigger/impact, "
    "and fix direction in 1-3 terse lines. Use Caveman compression but "
    "keep technical literals exact."
)

PROSE_POLISHED_DIRECTIVE = (
    "[TURN CLASSIFICATION: prose-polished] This turn addresses a polished "
    "audience (leadership, stakeholders, customers, external memo). "
    "Respond in professional, readable prose. Complete sentences with "
    "articles preserved. No Caveman compression. No filler, no hedging, "
    "no chatter, no bullet points unless requested. Match the tone asked "
    "(blameless, reassuring, reflective). Do NOT emit Hewn IR."
)

PROSE_POLISHED_CODE_DIRECTIVE = (
    "[TURN CLASSIFICATION: prose-polished+code] This turn addresses a "
    "polished audience (leadership, customer, stakeholder) AND asks for "
    "an executable artifact inline (code, config, snippet). Respond with "
    "professional readable prose (complete sentences, articles preserved, "
    "no Caveman compression, no filler) followed by one or more fenced "
    "code blocks (```lang ... ```). Match the tone asked (blameless, "
    "reassuring). Do NOT emit Hewn IR atoms — code must render verbatim."
)

DIRECTIVES: dict[str, str] = {
    "ir": IR_DIRECTIVE,
    "prose_code": PROSE_CODE_DIRECTIVE,
    "prose_caveman": PROSE_CAVEMAN_DIRECTIVE,
    "prose_findings": PROSE_FINDINGS_DIRECTIVE,
    "prose_polished": PROSE_POLISHED_DIRECTIVE,
    "prose_polished_code": PROSE_POLISHED_CODE_DIRECTIVE,
}


def build_output(label: str) -> dict:
    directive = DIRECTIVES.get(label, PROSE_CAVEMAN_DIRECTIVE)
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": directive,
        }
    }


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        event = {}
    prompt = event.get("prompt") or ""
    label = classify(prompt)
    print(json.dumps(build_output(label)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
