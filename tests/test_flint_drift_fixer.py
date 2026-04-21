"""Tests for the Flint drift-fix UserPromptSubmit hook classifier."""
from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

HOOK_PATH = (
    Path(__file__).resolve().parents[1]
    / "integrations"
    / "claude-code"
    / "hooks"
    / "flint_drift_fixer.py"
)


def _load_hook_module():
    spec = importlib.util.spec_from_file_location("flint_drift_fixer", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


hook = _load_hook_module()


IR_PROMPTS = [
    # Classic debug / review / fix — no code artifact asked
    "Debug this production issue: users report 502s on /checkout",
    "Review this diff for concurrency bugs",
    "Audit the JWT auth module for security vulnerabilities",
    "Fix the race condition in auth/session_refresh.py",
    "Refactor this handler to split billing from fulfillment",
    # Architecture / design
    "Describe the target architecture: service boundaries, sync vs async protocols, data ownership",
    "Propose the precise data ownership split. Each table has exactly one owner",
    "Design the order-to-payment flow using a saga pattern. Show the state machine",
    "Critique the consistency model: where are the dangerous eventual-consistency windows",
    # Monitoring / metrics
    "Which 5 SLOs tell me the split is healthy? What alert thresholds",
    "What canary-vs-control comparison query should I run day 1",
    # Postmortem investigation (IR turns, not the write-up)
    "Walk through what the trace tells you happened",
    "Root cause hypothesis? Consider the interaction between the reaper and the pool",
    "Propose the minimal fix that prevents recurrence",
    # Security-specific
    "What specific attack vectors does this JWT implementation expose?",
    # With embedded code block
    "```python\ndef verify(tok): jwt.decode(tok, SECRET)\n```\nWhat's wrong here?",
    # Italian
    "Spiega perché questo codice ha un race condition",
    "Cosa monitoro in prod dopo il deploy?",
    # Exploratory-technical (vibe-coding shapes that v0.8.2 missed)
    "Studia questa directory. Dimmi come potrei migliorare la flint CLI.",
    "Fammi un audit veloce del repo: cosa è solido, cosa è fragile, cosa toglierei.",
    "Cosa è fragile in questo progetto?",
]

PROSE_CODE_PROMPTS = [
    # Asks for code artifact alongside a technical task
    "Write regression tests (pytest) for algo=none rejection",
    "Propose the fix. Show updated jwt_service.py",
    "Show the code/config change that prevents recurrence",
    "Implement the saga coordinator; show the full class",
    "Write the patch that switches HS256 to RS256",
    "Apply the fix and show the updated module",
    "Draft an RFC and include sample code for the migration",
]

PROSE_POLISHED_PROMPTS = [
    # Leadership / memo / customer-facing, NO code artifact
    "Write a 2-paragraph summary for non-technical leadership: what we're doing, why, risks",
    "Write a memo for leadership. Tone: professional, no code. Cover what we found",
    "Draft a customer-facing post-mortem: blameless, factual, 4-5 paragraphs, no code, no IR",
]

PROSE_POLISHED_CODE_PROMPTS = [
    # Polished audience + inline code artifact
    "Customer-facing memo: include the exact nginx config we deployed inline. 2 paragraphs.",
    "Draft a 3-paragraph post-mortem for leadership; include sample code showing the fix.",
    "Write a stakeholder update with the patch snippet inline. Professional tone.",
]

PROSE_CAVEMAN_PROMPTS = [
    # Internal retrospective / reflective (not customer-facing)
    "Internal retrospective: what process changes would have caught this. Prose, reflective tone, narrative",
    # Pedagogical / tutorial
    "Explain to a junior dev how OAuth flows work",
    "Write a tutorial walkthrough of how TLS handshake works",
    # Brainstorm / discussion
    "Let's brainstorm options for the migration strategy",
    "Think out loud about the tradeoff between Kafka and RabbitMQ here",
    "Ragiona sul tradeoff tra event-sourcing e CRUD per questo dominio",
    # Chat / casual
    "What do you think about our approach so far?",
    "Give me a readable paragraph describing what we built last week",
    # Explicit disavowal
    "Answer in prose, no Flint IR, no markdown headers",
]

PROSE_FINDINGS_PROMPTS = [
    # Ranked/enumerated independent findings: technical, but not IR-shaped.
    "Find every security issue in this code, rank by severity",
    "Quali sono i 3 bug più probabili che un utente incontrerà nel primo mese?",
    "Audit this codebase and rank top issues",
    "What 3 bugs would a user most likely hit?",
    "Rank the top 5 launch blockers before we ship",
    "List the main failure modes with evidence and fix direction",
    "Flag the security issues in this PR, ranked by severity",
    "Classifica i rischi principali per probabilità e impatto",
]


@pytest.mark.parametrize("prompt", IR_PROMPTS)
def test_ir_prompts_classified_as_ir(prompt: str) -> None:
    assert hook.classify(prompt) == "ir", f"expected 'ir' for: {prompt!r}"


@pytest.mark.parametrize("prompt", PROSE_CODE_PROMPTS)
def test_prose_code_prompts_classified_as_prose_code(prompt: str) -> None:
    assert hook.classify(prompt) == "prose_code", f"expected 'prose_code' for: {prompt!r}"


@pytest.mark.parametrize("prompt", PROSE_POLISHED_PROMPTS)
def test_prose_polished_prompts_classified_as_prose_polished(prompt: str) -> None:
    assert hook.classify(prompt) == "prose_polished", f"expected 'prose_polished' for: {prompt!r}"


@pytest.mark.parametrize("prompt", PROSE_POLISHED_CODE_PROMPTS)
def test_prose_polished_code_prompts_classified_as_prose_polished_code(prompt: str) -> None:
    assert hook.classify(prompt) == "prose_polished_code", f"expected 'prose_polished_code' for: {prompt!r}"


@pytest.mark.parametrize("prompt", PROSE_CAVEMAN_PROMPTS)
def test_prose_caveman_prompts_classified_as_prose_caveman(prompt: str) -> None:
    assert hook.classify(prompt) == "prose_caveman", f"expected 'prose_caveman' for: {prompt!r}"


@pytest.mark.parametrize("prompt", PROSE_FINDINGS_PROMPTS)
def test_prose_findings_prompts_classified_as_prose_findings(prompt: str) -> None:
    assert hook.classify(prompt) == "prose_findings", f"expected 'prose_findings' for: {prompt!r}"


def test_empty_prompt_is_prose_caveman() -> None:
    assert hook.classify("") == "prose_caveman"
    assert hook.classify(None) == "prose_caveman"


def test_build_output_for_ir() -> None:
    out = hook.build_output("ir")
    hso = out["hookSpecificOutput"]
    assert hso["hookEventName"] == "UserPromptSubmit"
    ctx = hso["additionalContext"]
    assert "IR-shape" in ctx
    assert "@flint v0 hybrid" in ctx


def test_build_output_for_prose_code() -> None:
    ctx = hook.build_output("prose_code")["hookSpecificOutput"]["additionalContext"]
    assert "prose+code" in ctx
    assert "fenced code block" in ctx
    assert "Do NOT emit Flint IR" in ctx


def test_build_output_for_prose_caveman() -> None:
    ctx = hook.build_output("prose_caveman")["hookSpecificOutput"]["additionalContext"]
    assert "prose-caveman" in ctx
    assert "Caveman-compressed" in ctx
    assert "Do NOT emit Flint IR" in ctx


def test_build_output_for_prose_findings() -> None:
    ctx = hook.build_output("prose_findings")["hookSpecificOutput"]["additionalContext"]
    assert "prose-findings" in ctx
    assert "numbered findings list" in ctx
    assert "Do NOT emit Flint IR" in ctx


def test_build_output_for_prose_polished() -> None:
    ctx = hook.build_output("prose_polished")["hookSpecificOutput"]["additionalContext"]
    assert "prose-polished" in ctx
    assert "professional" in ctx.lower()
    assert "Caveman compression" in ctx or "No Caveman" in ctx
    assert "Do NOT emit Flint IR" in ctx


def test_build_output_for_prose_polished_code() -> None:
    ctx = hook.build_output("prose_polished_code")["hookSpecificOutput"]["additionalContext"]
    assert "prose-polished+code" in ctx
    assert "professional" in ctx.lower()
    assert "fenced code block" in ctx
    assert "caveman compression" in ctx.lower()
    assert "Do NOT emit Flint IR" in ctx


def test_build_output_unknown_label_falls_back_to_caveman() -> None:
    ctx = hook.build_output("unknown")["hookSpecificOutput"]["additionalContext"]
    assert "prose-caveman" in ctx


def test_main_reads_stdin_and_writes_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    event = {"prompt": "Audit this code for security issues", "cwd": "/tmp"}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event)))
    captured = io.StringIO()
    monkeypatch.setattr("sys.stdout", captured)
    rc = hook.main()
    assert rc == 0
    out = json.loads(captured.getvalue())
    assert out["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "IR-shape" in out["hookSpecificOutput"]["additionalContext"]


def test_main_handles_malformed_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("not valid json"))
    captured = io.StringIO()
    monkeypatch.setattr("sys.stdout", captured)
    rc = hook.main()
    assert rc == 0
    out = json.loads(captured.getvalue())
    # Empty prompt -> caveman default
    assert "prose-caveman" in out["hookSpecificOutput"]["additionalContext"]


def test_polished_override_wins_over_ir_signal() -> None:
    # Has debug keywords but explicit "non-technical leadership memo"
    prompt = (
        "We had a production outage; write a memo for non-technical leadership "
        "explaining what happened. 3 paragraphs, no code."
    )
    assert hook.classify(prompt) == "prose_polished"
