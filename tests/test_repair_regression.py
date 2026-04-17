"""Regression tests for repair-layer bugs flagged in post-launch review.

Each case captures an atom shape LLMs emit in the wild that used to either
parse-fail outright or be silently mangled by the repair layer.
"""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from flint.cli import main
from flint.normalize import repair_direct_flint_text
from flint.parser import FlintParseError, parse_document


class RepairRegressionTests(unittest.TestCase):
    def _assert_parses_after_repair(self, raw: str, category: str) -> str:
        repaired = repair_direct_flint_text(raw, category)
        try:
            parse_document(repaired)
        except FlintParseError as exc:
            self.fail(f"repaired document failed to parse: {exc}\nrepaired:\n{repaired}")
        return repaired

    def test_architecture_quoted_suffix_atoms_preserved(self) -> None:
        """`team_"9"`, `ddl_"12 weeks"`, `store_"PostgreSQL"` must repair into
        proper calls instead of dropping the whole C clause."""
        raw = (
            "@flint v0 hybrid\n"
            "G: default_arch\n"
            'C: team_"9" ∧ ddl_"12 weeks" ∧ store_"PostgreSQL"\n'
            "P: modular_monolith ∧ bounded_contexts\n"
            "V: ddl_fit ∧ audit_isolation\n"
            "A: choose_modular_monolith ∧ document_boundaries\n"
        )
        repaired = self._assert_parses_after_repair(raw, "architecture")
        self.assertIn('team("9")', repaired)
        self.assertIn('ddl("12 weeks")', repaired)
        self.assertIn('store("PostgreSQL")', repaired)

    def test_refactor_quoted_suffix_preserves_literal(self) -> None:
        """`db_err_forwards_"next(err)"` must keep the quoted literal intact."""
        raw = (
            "@flint v0 hybrid\n"
            "G: reconcileBatch_async\n"
            'C: callback_style ∧ db_err_forwards_"next(err)"\n'
            "P: convert_to_async ∧ await_each_step\n"
            "V: error_forwarded_via_next\n"
            "A: rewrite_async_await ∧ wrap_try_catch\n"
        )
        repaired = self._assert_parses_after_repair(raw, "refactoring")
        self.assertIn('db_err_forwards("next(err)")', repaired)

    def test_debug_valid_passes_not_eaten_by_outcome_regex(self) -> None:
        """The outcome-suffix regex used to match `valid_pass` inside
        `valid_passes` and leave dangling `es`. Verify both raw and repaired
        parse cleanly and the atom survives verbatim."""
        raw = (
            "@flint v0 hybrid\n"
            "G: fix_skew\n"
            "C: webhook_verify ∧ valid_passes\n"
            "P: widen_window ∧ reg_test\n"
            "V: valid_passes ∧ boundary_ok\n"
            "A: adjust_check ∧ add_test\n"
        )
        repaired = self._assert_parses_after_repair(raw, "debugging")
        self.assertIn("valid_passes", repaired)
        self.assertNotIn("edge(valid,pass)es", repaired)


class HybridWithoutAuditTests(unittest.TestCase):
    def test_hybrid_without_audit_parses(self) -> None:
        """The shipped /sigil skill produces 6-line hybrid documents with no
        trailing [AUDIT] block. These must parse without error."""
        raw = (
            "@flint v0 hybrid\n"
            "G: webhook_skew_fix\n"
            "C: webhook_verify ∧ valid_webhook_rejected\n"
            "P: widen_tolerance ∧ allow_provider_skew\n"
            "V: edge(-299s,200) ∧ edge(301s,401)\n"
            "A: adjust_skew_check ∧ add_regression_test\n"
        )
        doc = parse_document(raw)
        self.assertIsNone(doc.audit)
        self.assertEqual(len(doc.clauses), 5)


class AuditExplainTests(unittest.TestCase):
    def test_explain_panels_and_anchor_check(self) -> None:
        from pathlib import Path
        import tempfile

        sample = (
            "@flint v0 hybrid\n"
            "G: webhook_skew_fix\n"
            'C: webhook_verify ∧ team_"9"\n'
            "P: widen_tolerance ∧ reg_test\n"
            "V: edge(-299s,200) ∧ edge(301s,401)\n"
            "A: adjust_skew_check ∧ add_regression_test\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".flint", delete=False) as fh:
            fh.write(sample)
            path = Path(fh.name)
        try:
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main([
                    "audit", str(path), "--explain",
                    "--anchor", "401", "--anchor", "300", "--category", "architecture",
                ])
            out = buffer.getvalue()
        finally:
            path.unlink()
        self.assertEqual(exit_code, 0)
        self.assertIn("=== RAW", out)
        self.assertIn("=== REPAIRED", out)
        self.assertIn("=== PARSE", out)
        self.assertIn("=== ANCHORS", out)
        self.assertIn("=== PROSE AUDIT", out)
        self.assertIn("401", out)
        self.assertIn("hit:", out)
        self.assertIn("missed:", out)


if __name__ == "__main__":
    unittest.main()
