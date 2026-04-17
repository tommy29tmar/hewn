from __future__ import annotations

import unittest
from pathlib import Path

from flint.normalize import repair_direct_flint_text
from flint.parser import FlintParseError, parse_document
from flint.render import generate_audit, render_expr


ROOT = Path(__file__).resolve().parents[1]


class ParserTests(unittest.TestCase):
    def test_parse_debugging_example(self) -> None:
        document = parse_document(ROOT / "examples" / "debugging.flint")
        self.assertEqual(document.header.mode, "hybrid")
        self.assertEqual(len(document.codebook), 5)
        self.assertEqual(len(document.clauses), 8)
        self.assertIn("auth middleware expiry handling", document.audit)

    def test_memory_mode_rejects_non_memory_clause(self) -> None:
        source = "@flint v0 memory\nG: fix(auth)\n"
        with self.assertRaises(FlintParseError):
            parse_document(source)

    def test_parse_document_does_not_treat_long_single_line_text_as_path(self) -> None:
        source = "x" * 300
        with self.assertRaises(FlintParseError):
            parse_document(source)

    def test_audit_generation_expands_codebook(self) -> None:
        document = parse_document(ROOT / "examples" / "memory_capsules.flint")
        audit = generate_audit(document)
        self.assertIn("compat(v2_clients)", audit)
        self.assertIn("test(boundary_expiry)", audit)

    def test_prefix_and_postfix_markers_parse(self) -> None:
        document = parse_document("@flint v0 draft\nR: ! regression(auth)\nQ: refresh_rotation ?\n")
        self.assertEqual(document.clauses[0].tag, "R")
        self.assertEqual(document.clauses[1].tag, "Q")
        self.assertIn("high-risk", render_expr(document.clauses[0].expr))
        self.assertIn("uncertain", render_expr(document.clauses[1].expr))

    def test_quoted_literal_arguments_parse(self) -> None:
        source = '@flint v0 hybrid\nC: timeline("4 months") ∧ store("PostgreSQL")\n[AUDIT]\nshort\n'
        document = parse_document(source)
        self.assertEqual(document.header.mode, "hybrid")
        self.assertEqual(document.clauses[0].tag, "C")
        rendered = render_expr(document.clauses[0].expr)
        self.assertIn('"4 months"', rendered)
        self.assertIn('"PostgreSQL"', rendered)

    def test_repair_direct_flint_text_strips_standalone_flint_label(self) -> None:
        source = "SIGIL:\nG: webhook_verify | provider_skew\nC: abs(now-ts)>300 => 401\nP: min_fix\n[AUDIT]\nshort\n"
        repaired = repair_direct_flint_text(source, category="debugging")
        document = parse_document(repaired)
        self.assertEqual(document.header.mode, "hybrid")
        self.assertEqual(document.clauses[0].tag, "G")
        self.assertIn("gt(abs(now-ts),300)", repaired)


if __name__ == "__main__":
    unittest.main()
