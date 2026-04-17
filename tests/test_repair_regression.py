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

    def test_debug_suffix_literal_rewrites_into_call(self) -> None:
        """Forms like `"24h"_grace` should repair into valid calls so debug
        rows materialize instead of staying raw."""
        raw = (
            "@flint v0 hybrid\n"
            "G: min_fix\n"
            'C: overdue_middleware ∧ rule_402 ∧ "24h"_grace ∧ boundary_loop\n'
            'P: grace_exact ∧ no_loop ∧ "402"_on_overdue\n'
            "V: reg_test ∧ boundary_pass ∧ grace_honored\n"
            'A: patch_middleware ∧ add_grace24h ∧ emit_"402" ∧ add_reg_test\n'
        )
        repaired = self._assert_parses_after_repair(raw, "debugging")
        self.assertIn('grace("24h")', repaired)
        self.assertIn('on_overdue("402")', repaired)
        self.assertIn('emit("402")', repaired)

    def test_numeric_letter_suffix_in_comparator(self) -> None:
        """`skew<=30s` must repair into `le(skew,30s)` with `s` included, not
        dangling. Earlier regex only accepted `[0-9]+` on the numeric side."""
        raw = (
            "@flint v0 hybrid\n"
            "G: fix_skew_boundary\n"
            'C: min_diff ∧ keep("401") ∧ skew<=30s\n'
            "P: normalize_ms ∧ expMs+30s<nowMs\n"
            "V: boundary_pass ∧ reg_test\n"
            "A: widen_window ∧ add_reg_test\n"
        )
        repaired = self._assert_parses_after_repair(raw, "debugging")
        self.assertIn("le(skew,30s)", repaired)
        self.assertIn("lt(expMs+30s,nowMs)", repaired)

    def test_comparator_with_quoted_right_hand(self) -> None:
        """`ddl<="9 weeks"` must match the comparator rewrite and not leave a
        dangling quoted token that the parser misreads."""
        raw = (
            "@flint v0 hybrid\n"
            "G: default_arch\n"
            'C: team(6) ∧ ddl("9 weeks") ∧ store("PostgreSQL")\n'
            "P: pt_mlops ∧ worker_sidecar\n"
            'V: team<=6 ∧ ddl<="9 weeks" ∧ pg_only\n'
            "A: monolith_api ∧ pg_queue\n"
        )
        repaired = self._assert_parses_after_repair(raw, "architecture")
        self.assertIn('le(ddl,"9 weeks")', repaired)
        self.assertIn("le(team,6)", repaired)

    def test_bracket_list_syntax_rewrites_to_call(self) -> None:
        """`anchors[async|await|"next(err)"]` should repair into
        `anchors(async,await,"next(err)")`."""
        raw = (
            "@flint v0 hybrid\n"
            "G: reconcile_batch_refactor\n"
            'C: target(reconcileBatch) ∧ anchors[async|await|"next(err)"] ∧ minimal_change\n'
            "P: load_batch ∧ db.fetchRows\n"
            "V: preserve_order ∧ no_double_next\n"
            "A: async_await ∧ try_catch\n"
        )
        repaired = self._assert_parses_after_repair(raw, "refactoring")
        self.assertIn('anchors(async,await,"next(err)")', repaired)

    def test_colon_slash_list_syntax_rewrites_to_call(self) -> None:
        """`anchors:async/await/"next(err)"` should repair into
        `anchors(async,await,"next(err)")` like bracket form does."""
        raw = (
            "@flint v0 hybrid\n"
            "G: refactor_reconcileBatch\n"
            'C: anchors:async/await/"next(err)" ∧ minimal_change\n'
            "P: load_batch ∧ apply_rules\n"
            "V: order_preserved\n"
            "A: async_await ∧ wrap_try\n"
        )
        repaired = self._assert_parses_after_repair(raw, "refactoring")
        self.assertIn('anchors(async,await,"next(err)")', repaired)

    def test_quoted_slash_inside_call_repairs(self) -> None:
        """`style("async"/"await")` — slash between quoted args must become
        comma so the call parses."""
        raw = (
            "@flint v0 hybrid\n"
            "G: loadGatewayUser_refactor\n"
            'C: target(loadGatewayUser) ∧ style("async"/"await") ∧ minimal_change\n'
            "P: session_check ∧ db.findUser\n"
            "V: preserve_order\n"
            "A: try_catch_next\n"
        )
        repaired = self._assert_parses_after_repair(raw, "refactoring")
        self.assertIn('style("async","await")', repaired)

    def test_debug_outcome_suffix_ok_recognized(self) -> None:
        """`_ok` should be absorbed alongside existing `_pass`/`_fail`."""
        raw = (
            "@flint v0 hybrid\n"
            "G: refresh_fix\n"
            "C: normalize_ms ∧ min_diff\n"
            "P: widen_skew ∧ single_site\n"
            "V: refresh_no_loop_ok ∧ reg_test\n"
            "A: patch_middleware\n"
        )
        repaired = self._assert_parses_after_repair(raw, "debugging")
        self.assertIn("edge(refresh_no_loop,ok)", repaired)

    def test_prose_preamble_before_header_stripped(self) -> None:
        """Occasionally models ignore 'no prose' and emit a preamble line
        before the @flint header. Repair must strip it and parse clean."""
        raw = (
            "Here's the Flint:\n"
            "@flint v0 hybrid\n"
            "G: allow_skew\n"
            "C: webhook_verify\n"
            "P: widen_window\n"
            "V: no_regression\n"
            "A: reg_test\n"
        )
        repaired = self._assert_parses_after_repair(raw, "debugging")
        self.assertNotIn("Here's", repaired)

    def test_version_drift_v1_normalized_to_v0(self) -> None:
        """If the model writes `@flint v1 hybrid`, repair canonicalizes to v0."""
        raw = (
            "@flint v1 hybrid\n"
            "G: allow_skew\n"
            "C: webhook_verify\n"
            "P: widen_window\n"
            "V: no_regression\n"
            "A: reg_test\n"
        )
        repaired = self._assert_parses_after_repair(raw, "debugging")
        self.assertIn("@flint v0 hybrid", repaired)
        self.assertNotIn("@flint v1", repaired)

    def test_bare_flint_header_without_version_accepted(self) -> None:
        """`@flint hybrid` (missing version) canonicalizes to `@flint v0 hybrid`."""
        raw = (
            "@flint hybrid\n"
            "G: fix_x\n"
            "C: c1\n"
            "P: p1\n"
            "V: v1\n"
            "A: a1\n"
        )
        repaired = self._assert_parses_after_repair(raw, None)
        self.assertIn("@flint v0 hybrid", repaired)

    def test_debug_outcome_suffix_nested_parens(self) -> None:
        """`boundary(eq(exp,now))_pass` — the outcome regex must accept one
        level of nested parens on the left term."""
        raw = (
            "@flint v0 hybrid\n"
            "G: fix_expiry_boundary\n"
            "C: exp_compare ∧ reject_loop\n"
            "P: normalize_ms ∧ single_site\n"
            "V: boundary(eq(exp,now))_pass ∧ no_loop\n"
            "A: patch_cmp_site\n"
        )
        repaired = self._assert_parses_after_repair(raw, "debugging")
        self.assertIn("edge(boundary(eq(exp,now)),pass)", repaired)

    def test_refactor_order_chain_and_literal_suffixes_preserved(self) -> None:
        """Refactor chains use `>` as ordering, not numeric comparison, and
        quoted-literal affixes may carry extra suffixes."""
        raw = (
            "@flint v0 hybrid\n"
            "G: refactor_loadGatewayUser\n"
            'C: "async" ∧ "await" ∧ callback_style ∧ has_"next(err)"\n'
            'P: session_check>db.findUser>flags.load>audit.log>next ∧ preserve_"next(err)"_on_db_err ∧ minimal_change\n'
            'V: order_preserved ∧ db_err→"next(err)" ∧ uses_"async"_"await"\n'
            'A: convert_to_async ∧ await_each_step ∧ try_catch_db→"next(err)" ∧ call_next_last\n'
        )
        repaired = self._assert_parses_after_repair(raw, "refactoring")
        self.assertIn("session_check → db.findUser → flags.load → audit.log → next", repaired)
        self.assertIn('preserve_on_db_err("next(err)")', repaired)
        self.assertIn('uses("async","await")', repaired)


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
