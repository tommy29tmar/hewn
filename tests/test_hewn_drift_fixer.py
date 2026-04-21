"""Tests for the Hewn drift-fix UserPromptSubmit hook classifier."""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
import unittest.mock
from pathlib import Path

HOOK_PATH = (
    Path(__file__).resolve().parents[1]
    / "integrations"
    / "claude-code"
    / "hooks"
    / "hewn_drift_fixer.py"
)


def _load_hook_module():
    spec = importlib.util.spec_from_file_location("hewn_drift_fixer", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


hook = _load_hook_module()


IR_PROMPTS = [
    "Debug this production issue: users report 502s on /checkout",
    "Review this diff for concurrency bugs",
    "Audit the JWT auth module for security vulnerabilities",
    "Fix the race condition in auth/session_refresh.py",
    "Refactor this handler to split billing from fulfillment",
    "Describe the target architecture: service boundaries, sync vs async protocols, data ownership",
    "Propose the precise data ownership split. Each table has exactly one owner",
    "Design the order-to-payment flow using a saga pattern. Show the state machine",
    "Critique the consistency model: where are the dangerous eventual-consistency windows",
    "Which 5 SLOs tell me the split is healthy? What alert thresholds",
    "What canary-vs-control comparison query should I run day 1",
    "Walk through what the trace tells you happened",
    "Root cause hypothesis? Consider the interaction between the reaper and the pool",
    "Propose the minimal fix that prevents recurrence",
    "What specific attack vectors does this JWT implementation expose?",
    "```python\ndef verify(tok): jwt.decode(tok, SECRET)\n```\nWhat's wrong here?",
    "Spiega perché questo codice ha un race condition",
    "Cosa monitoro in prod dopo il deploy?",
    "Studia questa directory. Dimmi come potrei migliorare la hewn CLI.",
    "Fammi un audit veloce del repo: cosa è solido, cosa è fragile, cosa toglierei.",
    "Cosa è fragile in questo progetto?",
]

PROSE_CODE_PROMPTS = [
    "Write regression tests (pytest) for algo=none rejection",
    "Propose the fix. Show updated jwt_service.py",
    "Show the code/config change that prevents recurrence",
    "Implement the saga coordinator; show the full class",
    "Write the patch that switches HS256 to RS256",
    "Apply the fix and show the updated module",
    "Draft an RFC and include sample code for the migration",
]

PROSE_POLISHED_PROMPTS = [
    "Write a 2-paragraph summary for non-technical leadership: what we're doing, why, risks",
    "Write a memo for leadership. Tone: professional, no code. Cover what we found",
    "Draft a customer-facing post-mortem: blameless, factual, 4-5 paragraphs, no code, no IR",
]

PROSE_POLISHED_CODE_PROMPTS = [
    "Customer-facing memo: include the exact nginx config we deployed inline. 2 paragraphs.",
    "Draft a 3-paragraph post-mortem for leadership; include sample code showing the fix.",
    "Write a stakeholder update with the patch snippet inline. Professional tone.",
]

PROSE_CAVEMAN_PROMPTS = [
    "Internal retrospective: what process changes would have caught this. Prose, reflective tone, narrative",
    "Explain to a junior dev how OAuth flows work",
    "Write a tutorial walkthrough of how TLS handshake works",
    "Let's brainstorm options for the migration strategy",
    "Think out loud about the tradeoff between Kafka and RabbitMQ here",
    "Ragiona sul tradeoff tra event-sourcing e CRUD per questo dominio",
    "What do you think about our approach so far?",
    "Give me a readable paragraph describing what we built last week",
    "Answer in prose, no Hewn IR, no markdown headers",
]

PROSE_FINDINGS_PROMPTS = [
    "Find every security issue in this code, rank by severity",
    "Quali sono i 3 bug più probabili che un utente incontrerà nel primo mese?",
    "Audit this codebase and rank top issues",
    "What 3 bugs would a user most likely hit?",
    "Rank the top 5 launch blockers before we ship",
    "List the main failure modes with evidence and fix direction",
    "Flag the security issues in this PR, ranked by severity",
    "Classifica i rischi principali per probabilità e impatto",
]


class ClassifyTests(unittest.TestCase):
    def _expect(self, prompts, label):
        for prompt in prompts:
            with self.subTest(prompt=prompt, label=label):
                self.assertEqual(
                    hook.classify(prompt),
                    label,
                    f"expected {label!r} for: {prompt!r}",
                )

    def test_ir_prompts(self):
        self._expect(IR_PROMPTS, "ir")

    def test_prose_code_prompts(self):
        self._expect(PROSE_CODE_PROMPTS, "prose_code")

    def test_prose_polished_prompts(self):
        self._expect(PROSE_POLISHED_PROMPTS, "prose_polished")

    def test_prose_polished_code_prompts(self):
        self._expect(PROSE_POLISHED_CODE_PROMPTS, "prose_polished_code")

    def test_prose_caveman_prompts(self):
        self._expect(PROSE_CAVEMAN_PROMPTS, "prose_caveman")

    def test_prose_findings_prompts(self):
        self._expect(PROSE_FINDINGS_PROMPTS, "prose_findings")

    def test_empty_prompt_is_prose_caveman(self):
        self.assertEqual(hook.classify(""), "prose_caveman")
        self.assertEqual(hook.classify(None), "prose_caveman")

    def test_polished_override_wins_over_ir_signal(self):
        prompt = (
            "We had a production outage; write a memo for non-technical leadership "
            "explaining what happened. 3 paragraphs, no code."
        )
        self.assertEqual(hook.classify(prompt), "prose_polished")


class BuildOutputTests(unittest.TestCase):
    def test_ir(self):
        ctx = hook.build_output("ir")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("IR-shape", ctx)
        self.assertIn("@hewn v0 hybrid", ctx)

    def test_prose_code(self):
        ctx = hook.build_output("prose_code")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("prose+code", ctx)
        self.assertIn("fenced code block", ctx)
        self.assertIn("Do NOT emit Hewn IR", ctx)

    def test_prose_caveman(self):
        ctx = hook.build_output("prose_caveman")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("prose-caveman", ctx)
        self.assertIn("Caveman-compressed", ctx)
        self.assertIn("Do NOT emit Hewn IR", ctx)

    def test_prose_findings(self):
        ctx = hook.build_output("prose_findings")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("prose-findings", ctx)
        self.assertIn("numbered findings list", ctx)
        self.assertIn("Do NOT emit Hewn IR", ctx)

    def test_prose_polished(self):
        ctx = hook.build_output("prose_polished")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("prose-polished", ctx)
        self.assertIn("professional", ctx.lower())
        self.assertTrue("Caveman compression" in ctx or "No Caveman" in ctx)
        self.assertIn("Do NOT emit Hewn IR", ctx)

    def test_prose_polished_code(self):
        ctx = hook.build_output("prose_polished_code")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("prose-polished+code", ctx)
        self.assertIn("professional", ctx.lower())
        self.assertIn("fenced code block", ctx)
        self.assertIn("caveman compression", ctx.lower())
        self.assertIn("Do NOT emit Hewn IR", ctx)

    def test_unknown_label_falls_back_to_caveman(self):
        ctx = hook.build_output("unknown")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("prose-caveman", ctx)


class MainTests(unittest.TestCase):
    def test_reads_stdin_and_writes_stdout(self):
        event = {"prompt": "Audit this code for security issues", "cwd": "/tmp"}
        captured = io.StringIO()
        with unittest.mock.patch.object(sys, "stdin", io.StringIO(json.dumps(event))), \
             unittest.mock.patch.object(sys, "stdout", captured):
            rc = hook.main()
        self.assertEqual(rc, 0)
        out = json.loads(captured.getvalue())
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")
        self.assertIn("IR-shape", out["hookSpecificOutput"]["additionalContext"])

    def test_handles_malformed_stdin(self):
        captured = io.StringIO()
        with unittest.mock.patch.object(sys, "stdin", io.StringIO("not valid json")), \
             unittest.mock.patch.object(sys, "stdout", captured):
            rc = hook.main()
        self.assertEqual(rc, 0)
        out = json.loads(captured.getvalue())
        self.assertIn("prose-caveman", out["hookSpecificOutput"]["additionalContext"])


if __name__ == "__main__":
    unittest.main()
