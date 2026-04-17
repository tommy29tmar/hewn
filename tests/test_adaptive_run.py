from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "evals" / "build_adaptive_run.py"
SPEC = importlib.util.spec_from_file_location("sigil_eval_build_adaptive_run", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
BUILD_ADAPTIVE_RUN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BUILD_ADAPTIVE_RUN
SPEC.loader.exec_module(BUILD_ADAPTIVE_RUN)


class BuildAdaptiveRunTests(unittest.TestCase):
    def test_build_adaptive_run_uses_fallback_when_verifier_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tasks = root / "tasks.jsonl"
            primary = root / "primary.jsonl"
            fallback = root / "fallback.jsonl"
            baseline = root / "baseline.jsonl"
            out = root / "adaptive.jsonl"

            tasks.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "id": "t1",
                                "category": "debugging",
                                "mode": "hybrid",
                                "must_include": ["auth"],
                                "exact_literals": ["401"],
                            }
                        ),
                        json.dumps(
                            {
                                "id": "t2",
                                "category": "architecture",
                                "mode": "hybrid",
                                "must_include": ["modular"],
                                "exact_literals": ["PostgreSQL"],
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            primary.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "task_id": "t1",
                                "variant": "sigil-primary",
                                "transport": "sigil",
                                "structured_expected": True,
                                "content": (ROOT / "examples" / "debugging.flint").read_text(encoding="utf-8"),
                                "usage": {"output_tokens": 48, "input_tokens": 120},
                            }
                        ),
                        json.dumps(
                            {
                                "task_id": "t2",
                                "variant": "sigil-primary",
                                "transport": "sigil",
                                "structured_expected": True,
                                "content": "@flint v0 hybrid\nG: choose(arch)\nA: service_mesh\n\n[AUDIT]\nwrong\n",
                                "usage": {"output_tokens": 18, "input_tokens": 40},
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            fallback.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "task_id": "t1",
                                "variant": "sigil-fallback",
                                "transport": "plain",
                                "structured_expected": False,
                                "content": "Fallback path for t1.",
                                "usage": {"output_tokens": 12, "input_tokens": 30},
                            }
                        ),
                        json.dumps(
                            {
                                "task_id": "t2",
                                "variant": "sigil-fallback",
                                "transport": "sigil",
                                "structured_expected": True,
                                "content": (ROOT / "examples" / "architecture.flint").read_text(encoding="utf-8"),
                                "usage": {"output_tokens": 40, "input_tokens": 110},
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            baseline.write_text(
                "\n".join(
                    [
                        json.dumps({"task_id": "t1", "variant": "baseline-terse", "transport": "plain", "content": "base1"}),
                        json.dumps({"task_id": "t2", "variant": "baseline-terse", "transport": "plain", "content": "base2"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = BUILD_ADAPTIVE_RUN.main(
                    [
                        str(tasks),
                        str(out),
                        "--primary-run",
                        str(primary),
                        "--fallback-run",
                        str(fallback),
                        "--baseline-run",
                        str(baseline),
                        "--allow-repair",
                        "--min-must-include",
                        "0.5",
                        "--min-exact-literal",
                        "1.0",
                    ]
                )
            self.assertEqual(exit_code, 0)
            summary = json.loads(buffer.getvalue())
            self.assertEqual(summary["selected_primary"], 1)
            self.assertEqual(summary["selected_fallback"], 1)

            rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 4)
            adaptive_rows = [row for row in rows if row["variant"] == "sigil-adaptive"]
            self.assertEqual(adaptive_rows[0]["adaptive_selected_from"], "primary")
            self.assertEqual(adaptive_rows[1]["adaptive_selected_from"], "fallback")
            self.assertIn("must_include", adaptive_rows[1]["adaptive_rejection"])
            self.assertEqual(adaptive_rows[1]["adaptive_fallback_variant"], "sigil-fallback")

    def test_build_adaptive_run_supports_ordered_candidate_cascade(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tasks = root / "tasks.jsonl"
            tier1 = root / "tier1.jsonl"
            tier2 = root / "tier2.jsonl"
            tier3 = root / "tier3.jsonl"
            out = root / "adaptive.jsonl"

            tasks.write_text(
                json.dumps(
                    {
                        "id": "t1",
                        "category": "debugging",
                        "mode": "hybrid",
                        "must_include": ["auth"],
                        "exact_literals": ["401"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            tier1.write_text(
                json.dumps(
                    {
                        "task_id": "t1",
                        "variant": "sigil-nano",
                        "transport": "sigil",
                        "structured_expected": True,
                        "content": "@flint v0 hybrid\nG: fix(cache)\nA: patch\n\n[AUDIT]\nwrong\n",
                        "usage": {"output_tokens": 12, "input_tokens": 20},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            tier2.write_text(
                json.dumps(
                    {
                        "task_id": "t1",
                        "variant": "sigil-wire",
                        "transport": "sigil",
                        "structured_expected": True,
                        "content": (ROOT / "examples" / "debugging.flint").read_text(encoding="utf-8"),
                        "usage": {"output_tokens": 48, "input_tokens": 120},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            tier3.write_text(
                json.dumps(
                    {
                        "task_id": "t1",
                        "variant": "baseline-terse",
                        "transport": "plain",
                        "structured_expected": False,
                        "content": "plain fallback",
                        "usage": {"output_tokens": 10, "input_tokens": 30},
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = BUILD_ADAPTIVE_RUN.main(
                    [
                        str(tasks),
                        str(out),
                        "--candidate-run",
                        str(tier1),
                        "--candidate-run",
                        str(tier2),
                        "--candidate-run",
                        str(tier3),
                        "--allow-repair",
                        "--min-must-include",
                        "1.0",
                        "--min-exact-literal",
                        "1.0",
                    ]
                )
            self.assertEqual(exit_code, 0)
            summary = json.loads(buffer.getvalue())
            self.assertEqual(summary["selected_primary"], 0)
            self.assertEqual(summary["selected_fallback"], 1)
            self.assertEqual(summary["selected_tiers"]["sigil-wire"], 1)

            row = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row["adaptive_selected_variant"], "sigil-wire")
            self.assertEqual(row["adaptive_candidate_variants"], ["sigil-nano", "sigil-wire", "baseline-terse"])
            self.assertEqual(row["adaptive_rejection_chain"][0]["variant"], "sigil-nano")


if __name__ == "__main__":
    unittest.main()
