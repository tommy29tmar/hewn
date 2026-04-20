#!/usr/bin/env python3
"""Flint drift-fix hook — UserPromptSubmit classifier.

Reads a Claude Code UserPromptSubmit event from stdin, classifies the
turn as IR-shape or prose-shape using a score-based rule set, and emits
a hookSpecificOutput JSON that reasserts the Flint routing directive
as additionalContext. This pins the model's attention to the task
shape on every turn, preventing the T2+ drift observed when relying
on the system prompt alone.

Pure Python, no external deps. Runs in <10ms.

Score-based classifier:
- Positive signals pull toward IR (structural, analytical, debugging).
- Negative signals pull toward prose (writing, explanation, leadership).
- Threshold >= 2 -> IR, otherwise prose.

See tests/test_flint_drift_fixer.py for the classification corpus.
"""
from __future__ import annotations

import json
import re
import sys


IR_RULES: list[tuple[str, int]] = [
    (r"\bdebug(?:ging)?\b|\bdiagnose\b|\broot[- ]cause\b|\btrace(?:s|d)?\b.*(?:bug|error|outage|failure)|\boutage\b", 3),
    (r"\breview\b.*(?:code|diff|patch|pr|commit|architecture|design|module|service)", 3),
    (r"\baudit\b.*(?:code|security|auth|module|api|implementation)", 3),
    (r"\bcritique\b|\banalyz[e|ing]\b.*(?:consistency|risk|tradeoff|failure)", 3),
    (r"\bfix\b.*(?:bug|code|race|issue|vulnerabilit|defect|regression|leak)|\bresolve\b.*(?:bug|issue|race)", 3),
    (r"\brefactor\b|\bre-?design\b", 2),
    (r"\bdesign\b.*(?:architecture|schema|pattern|saga|state[- ]machine|migration|split|boundary|flow)", 3),
    (r"\bpropose\b.*(?:fix|architecture|split|schema|mitigation|boundary|ownership|pattern|structure)", 3),
    (r"\bdescribe\b.*(?:target|architecture|fix|state[- ]machine|consistency|flow|protocol|boundary)", 2),
    (r"\bvulnerabilit|bypass.*(?:auth|security|signature)|signature[- ]forger|algo[- ]confus|jwt.*(?:none|algo|implementation|decode|verify)|\brace[- ]condition\b|\bdeadlock\b|\binjection\b|\bexploit\b|\battack[- ]vector", 3),
    (r"\bsecurity\s+issues?\b|\bexploitabilit|rank\s+by\s+severity|\bforged?\s+signature\b", 3),
    (r"\bwhich\b.*(?:slo|metric|alert|canary|dashboard|gauge|signal)|\bwhat\b.*(?:metric|alert|canary|threshold|slo)", 3),
    (r"\bconsistency\b.*(?:window|bound|model|guarantee|violat)|eventual.*consist", 2),
    (r"```|\bdef\s+\w+\s*\(|\bclass\s+\w+\b|diff --git|^[+-][^-+]", 2),
    (r"\bwhat\s+(?:is\s+)?(?:wrong|the\s+bug|the\s+issue|the\s+problem|the\s+attack)\b", 3),
    (r"\brepro(?:duce|duction)?\b.*(?:test|case|script)|\bregression\s+tests?\b", 2),
    (r"\bpropose\b|\bhypothe[sz]iz|\bhypothesis\b", 2),
    (r"spieg[ao].*perch[eé]|cosa\s+monit|monit.*prod|cosa\s+controll|cos'?[eè]\s+che\s+non\s+va", 3),
    (r"\bsaga\b|\btwo[- ]?phase[- ]?commit\b|\b2pc\b|\bidempot|\bcompensat\w*|\bprojection\b", 2),
    (r"\bwalk[- ]through\b.*(?:trace|log|stack|error)|\bwhat\s+the\s+trace\b", 3),
]

PROSE_RULES: list[tuple[str, int]] = [
    (r"\bnon[- ]technical\b|\bstakeholders?\b|\bleadership\b|\bexecutive\b|\bc[- ]suite\b|\bcustomer[- ]facing\b", 5),
    (r"\bmemo\b|\bnarrative\b|\bessay\b|\bparagraph\b|\bbullet[- ]free\b|\bno\s+bullet\b|\bin\s+prose\b|\bno\s+markdown\b|\bno\s+code\b,?\s*no\s+ir", 4),
    (r"\bexplain\b.*(?:junior|beginner|newcomer|non[- ]tech|five\s+year|like.*im|come.*se)|\btutorial\b|\bwalkthrough\b.*(?:how|works|beginner)", 3),
    (r"\bbrainstorm\b|\bthink\s+out\s+loud\b|\bragion[ia]\s+sul\s+tradeoff|\bdiscussion\b", 3),
    (r"\bpost[- ]?mortem\b.*(?:write|draft|compose|customer|blameless)|\bretrospective\b.*(?:write|narrative|reflective)", 4),
    (r"\brfc\b.*(?:draft|write|compose)|\bdesign[- ]doc\b|\bone[- ]pager\b.*(?:leader|exec)", 3),
    (r"\breadable\b|\bprofessional\s+tone\b|\breassuring\b|\btone:\s*(?:blameless|professional|reflective|narrative)", 2),
    (r"\bno\s+ir\b|\bno\s+flint\b", 5),
]

# Signals that the user wants an executable code artifact in the answer
# (fix diff, regression test, updated file, implementation snippet).
# When one of these fires AND the IR score crosses threshold, the turn is
# routed to "prose_code" instead of "ir": prose analysis wrapping a
# fenced code block, because IR atoms break on multi-line verbatim code.
CODE_ARTIFACT_RULES: list[str] = [
    r"\b(?:show|display|produce|emit|provide)\s+(?:the\s+)?(?:updated|full|complete|new|final)\s+(?:code|file|method|function|class|module|source|impl\w*)",
    r"\b(?:show|display)\s+(?:the\s+)?(?:code|config|patch|diff|snippet)",
    r"\bwrite\s+(?:the\s+)?(?:code|tests?|snippet|function|method|patch|fix|script|implementation|regression\s+tests?|pytest|unit\s+tests?)",
    r"\bimplement\s+(?:the|a|an)\b",
    r"\bapply\s+the\s+(?:fix|change|patch|update)",
    r"\b(?:include|with)\s+(?:sample|example|inline|exact)\s+(?:code|config|snippet)\b",
    r"\bsample\s+(?:code|config|snippet)\b",
    r"\bupdated\s+(?:\w+\.\w+|jwt_\w+|auth\w*|handler|service|module|file)",
    r"\bpropose\s+the\s+fix.*(?:show|code|snippet|file)",
]

# Signals that prose should be polished/professional (memo, leadership,
# customer-facing) rather than Caveman-compressed.
POLISHED_AUDIENCE_RULES: list[str] = [
    r"\bleadership\b|\bnon[- ]technical\b|\bstakeholders?\b|\bexecutive\b|\bc[- ]suite\b",
    r"\bcustomer[- ]facing\b|\bcustomer[- ]?(?:memo|letter|update|announcement)\b",
    r"\bmemo\b.*(?:leadership|stakeholder|customer)|\bdraft\s+a\s+(?:memo|letter|announcement)",
    r"\bpost[- ]?mortem\b.*(?:customer|blameless|public|external)",
    r"\bprofessional\s+tone\b|\bblameless\s+tone\b|\breassuring\b",
    r"\b(?:2|3|4|5|two|three|four|five)\s+paragraphs?\b",
]

IR_THRESHOLD = 2


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, re.IGNORECASE | re.MULTILINE) for p in patterns)


def classify(prompt: str) -> str:
    """Return one of 'ir' | 'prose_code' | 'prose_polished' | 'prose_caveman'.

    Decision order (first match wins):
      1. Strongly polished audience (leadership / customer-facing + memo / paragraphs)
         -> 'prose_polished'. Overrides everything else: a memo-for-leadership
         that mentions bugs is still a memo.
      2. Code artifact requested (show/write code, tests, updated file)
         -> 'prose_code'. Verbatim code does not fit inside IR atoms.
      3. Technical score >= IR_THRESHOLD -> 'ir'. Crisp goal + verifiable endpoint.
      4. Any polished-audience hint -> 'prose_polished'.
      5. Default -> 'prose_caveman' (terse, compressed prose).
    """
    text = prompt or ""
    ir_score = 0
    prose_score = 0
    for pattern, weight in IR_RULES:
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            ir_score += weight
    for pattern, weight in PROSE_RULES:
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            prose_score += weight

    wants_code = _matches_any(text, CODE_ARTIFACT_RULES)
    polished_audience = _matches_any(text, POLISHED_AUDIENCE_RULES)

    if polished_audience and prose_score >= 4:
        return "prose_polished"
    if wants_code:
        return "prose_code"
    if ir_score - prose_score >= IR_THRESHOLD:
        return "ir"
    if polished_audience:
        return "prose_polished"
    return "prose_caveman"


IR_DIRECTIVE = (
    "[TURN CLASSIFICATION: IR-shape] This turn has a crisp technical goal "
    "and verifiable endpoint. Respond in Flint IR: emit '@flint v0 hybrid' "
    "+ G/C/P/V/A clauses (or call the submit_flint_ir MCP tool if "
    "available). Do NOT respond in prose for this turn. Keep atoms in "
    "lowercase_snake_case or call form f(\"x\") or quoted literals. "
    "No code blocks inside atoms."
)

PROSE_CODE_DIRECTIVE = (
    "[TURN CLASSIFICATION: prose+code] This turn asks for an executable "
    "artifact (fix, test, updated file, snippet). Respond with a brief "
    "Caveman-compressed prose analysis (2-4 lines) followed by one or "
    "more fenced code blocks (```lang ... ```). Do NOT emit Flint IR "
    "atoms — code must render verbatim. Keep the analysis terse: drop "
    "articles, no filler. Code block first when the user asked to 'show' it."
)

PROSE_CAVEMAN_DIRECTIVE = (
    "[TURN CLASSIFICATION: prose-caveman] This turn asks for casual "
    "writing, brainstorming, quick explanation, or internal retrospective. "
    "Respond in Caveman-compressed prose. Drop articles (the/a/an/is/are). "
    "No markdown headers (# or ##). No bold. No filler intros or summaries. "
    "One idea per line. Do NOT emit Flint IR or call submit_flint_ir."
)

PROSE_POLISHED_DIRECTIVE = (
    "[TURN CLASSIFICATION: prose-polished] This turn addresses a polished "
    "audience (leadership, stakeholders, customers, external memo). "
    "Respond in professional, readable prose. Complete sentences with "
    "articles preserved. No Caveman compression. No filler, no hedging, "
    "no chatter, no bullet points unless requested. Match the tone asked "
    "(blameless, reassuring, reflective). Do NOT emit Flint IR or call "
    "submit_flint_ir."
)

DIRECTIVES: dict[str, str] = {
    "ir": IR_DIRECTIVE,
    "prose_code": PROSE_CODE_DIRECTIVE,
    "prose_caveman": PROSE_CAVEMAN_DIRECTIVE,
    "prose_polished": PROSE_POLISHED_DIRECTIVE,
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
