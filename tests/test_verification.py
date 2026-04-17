from __future__ import annotations

import unittest
from pathlib import Path

from flint.verification import assess_output, verification_failures, verification_passes


ROOT = Path(__file__).resolve().parents[1]


class VerificationTests(unittest.TestCase):
    def test_assess_output_marks_valid_direct_sigil(self) -> None:
        task = {
            "id": "t1",
            "category": "debugging",
            "mode": "hybrid",
            "must_include": ["auth"],
            "exact_literals": ["401"],
        }
        row = {
            "variant": "sigil-debug",
            "transport": "sigil",
            "structured_expected": True,
            "content": (ROOT / "examples" / "debugging.flint").read_text(encoding="utf-8"),
            "usage": {"output_tokens": 48, "input_tokens": 120},
        }
        metrics = assess_output(task, row, root=ROOT)
        self.assertTrue(metrics["parse_ok"])
        self.assertTrue(metrics["mode_match"])
        self.assertGreaterEqual(metrics["must_include_rate"], 1.0)
        self.assertGreaterEqual(metrics["exact_literal_rate"], 1.0)
        self.assertTrue(verification_passes(metrics, allow_repair=True))

    def test_verification_failures_catches_missing_literals(self) -> None:
        task = {
            "id": "t2",
            "category": "architecture",
            "mode": "hybrid",
            "must_include": ["modular"],
            "exact_literals": ["PostgreSQL"],
        }
        row = {
            "variant": "sigil-arch",
            "transport": "sigil",
            "structured_expected": True,
            "content": "@flint v0 hybrid\nG: choose(arch)\nA: service_mesh\n\n[AUDIT]\nwrong\n",
            "usage": {"output_tokens": 18, "input_tokens": 40},
        }
        metrics = assess_output(task, row, root=ROOT)
        failures = verification_failures(metrics, min_must_include=0.5, min_exact_literal=1.0, allow_repair=True)
        self.assertIn("must_include", failures)
        self.assertIn("exact_literals", failures)
        self.assertFalse(verification_passes(metrics, min_must_include=0.5, min_exact_literal=1.0, allow_repair=True))


if __name__ == "__main__":
    unittest.main()
