from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "evals" / "rerender_run.py"
SPEC = importlib.util.spec_from_file_location("sigil_eval_rerender_run", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
RERENDER_RUN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RERENDER_RUN
SPEC.loader.exec_module(RERENDER_RUN)


class RerenderRunTests(unittest.TestCase):
    def test_rerender_row_updates_structured_content(self) -> None:
        row = {
            "task_id": "debug-task",
            "variant": "sigil-debug-wire-lite",
            "transport": "schema-debug_wire_lite",
            "structured_data": {
                "m": "hybrid",
                "t": "skew30",
                "c": ["bc", "sec"],
                "h": "exp_lt_no_skew",
                "p": ["add(skew30)"],
                "v": ["edge(-31s_401)"],
                "r": ["timeunit_bug"],
                "a": ["allow30s_skew"],
            },
        }
        updated = RERENDER_RUN.rerender_row(row)
        content = updated["content"]
        self.assertIn("@sigil v0 hybrid", content)
        self.assertIn("backward compatibility", content)
        self.assertIn("30-second grace window", content)

    def test_rerender_row_re_materializes_direct_sigil(self) -> None:
        row = {
            "task_id": "debug-task",
            "variant": "sigil-debug-gemini-nano",
            "transport": "sigil",
            "prompt_path": "prompts/debug_direct_sigil_gemini_nano.txt",
            "content": '[d] "<"\nG: "401"\nC: auth\nP: grace\nV: regression test\nA: keep_401 edge(-30s_200) edge(-31s_401)',
        }
        updated = RERENDER_RUN.rerender_row(row)
        content = updated["content"]
        self.assertTrue(content.startswith("@sigil v0 hybrid"))
        self.assertNotIn("[d]", content)
        self.assertIn("A: keep_401 ∧ edge(-30s_200) ∧ edge(-31s_401)", content)

    def test_main_rerenders_jsonl_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "in.jsonl"
            out = tmp_path / "out.jsonl"
            row = {
                "task_id": "review-task",
                "variant": "sigil-review-wire-lite",
                "transport": "schema-review_wire_lite",
                "structured_data": {
                    "m": "hybrid",
                    "f": "hdr_override:authz_bypass",
                    "e": "spoof(x-user-id)->impersonation",
                    "p": ["drop_hdr", "sess_only"],
                    "v": ["401_without_x-user-id"],
                    "r": ["authz_bypass"],
                    "a": ["revert_or_ignore_client_x-id"],
                },
            }
            src.write_text(json.dumps(row) + "\n", encoding="utf-8")
            exit_code = RERENDER_RUN.main([str(src), str(out)])
            self.assertEqual(exit_code, 0)
            rows = RERENDER_RUN.load_jsonl(out)
            self.assertEqual(len(rows), 1)
            self.assertIn("header auth risk", rows[0]["content"])


if __name__ == "__main__":
    unittest.main()
