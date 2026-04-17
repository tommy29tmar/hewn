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
MODULE_PATH = ROOT / "evals" / "suggest_profile.py"
SPEC = importlib.util.spec_from_file_location("sigil_eval_suggest_profile", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
SUGGEST_PROFILE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SUGGEST_PROFILE
SPEC.loader.exec_module(SUGGEST_PROFILE)


class SuggestProfileTests(unittest.TestCase):
    def test_efficiency_profile_prefers_lower_cost_with_parseability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            tasks_path = tmp_path / "tasks.jsonl"
            run_path = tmp_path / "runs.jsonl"
            out_path = tmp_path / "profile.json"

            tasks_path.write_text(
                json.dumps(
                    {
                        "id": "debug-task",
                        "category": "debugging",
                        "mode": "hybrid",
                        "prompt": "x",
                        "must_include": ["grace"],
                        "exact_literals": ["401"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            run_rows = [
                {
                    "task_id": "debug-task",
                    "variant": "fast-parseable",
                    "content": '@flint v0 hybrid\nG: fix(auth)\nC: grace ∧ status("401")\nA: ok\n\n[AUDIT]\nshort\n',
                    "usage": {"input_tokens": 10, "output_tokens": 10, "total_tokens": 20},
                    "elapsed_ms": 1000,
                },
                {
                    "task_id": "debug-task",
                    "variant": "cheap-broken",
                    "content": "not sigil",
                    "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
                    "elapsed_ms": 10,
                },
            ]
            run_path.write_text("".join(json.dumps(row) + "\n" for row in run_rows), encoding="utf-8")

            with io.StringIO() as buffer, redirect_stdout(buffer):
                exit_code = SUGGEST_PROFILE.main(
                    [
                        str(tasks_path),
                        str(out_path),
                        "--objective",
                        "efficiency",
                        "--run",
                        str(run_path),
                    ]
                )
            self.assertEqual(exit_code, 0)
            profile = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(profile["categories"]["debugging"], "fast-parseable")

    def test_balanced_profile_preserves_custom_name(self) -> None:
        summary = {
            "debugging": {
                "a": {
                    "parse_rate": 1.0,
                    "repair_parse_rate": 1.0,
                    "mode_match_rate": 1.0,
                    "repair_mode_match_rate": 1.0,
                    "must_include_rate": 1.0,
                    "exact_literal_rate": 1.0,
                    "output_tokens": 100.0,
                    "effective_total_tokens": 500.0,
                    "elapsed_ms": 1000.0,
                },
                "b": {
                    "parse_rate": 1.0,
                    "repair_parse_rate": 1.0,
                    "mode_match_rate": 1.0,
                    "repair_mode_match_rate": 1.0,
                    "must_include_rate": 0.0,
                    "exact_literal_rate": 0.0,
                    "output_tokens": 10.0,
                    "effective_total_tokens": 10.0,
                    "elapsed_ms": 10.0,
                },
            }
        }
        profile = SUGGEST_PROFILE.build_profile(summary, objective="balanced", profile_name="balanced_v1")
        self.assertEqual(profile["name"], "balanced_v1")

    def test_efficiency_profile_prefers_lower_total_when_quality_floor_is_met(self) -> None:
        summary = {
            "architecture": {
                "low_output_higher_total": {
                    "parse_rate": 1.0,
                    "repair_parse_rate": 1.0,
                    "mode_match_rate": 1.0,
                    "repair_mode_match_rate": 1.0,
                    "must_include_rate": 1.0,
                    "exact_literal_rate": 1.0,
                    "output_tokens": 70.0,
                    "effective_total_tokens": 320.0,
                    "elapsed_ms": 1400.0,
                },
                "higher_output_lower_total": {
                    "parse_rate": 1.0,
                    "repair_parse_rate": 1.0,
                    "mode_match_rate": 1.0,
                    "repair_mode_match_rate": 1.0,
                    "must_include_rate": 1.0,
                    "exact_literal_rate": 1.0,
                    "output_tokens": 85.0,
                    "effective_total_tokens": 280.0,
                    "elapsed_ms": 900.0,
                },
            }
        }
        profile = SUGGEST_PROFILE.build_profile(summary, objective="efficiency", profile_name="efficiency_v2")
        self.assertEqual(profile["categories"]["architecture"], "higher_output_lower_total")

    def test_efficiency_profile_can_choose_plain_candidate_when_enabled(self) -> None:
        summary = {
            "debugging": {
                "baseline-terse": {
                    "structured_expected_rate": 0.0,
                    "parse_rate": 0.0,
                    "repair_parse_rate": 0.0,
                    "mode_match_rate": 0.0,
                    "repair_mode_match_rate": 0.0,
                    "must_include_rate": 0.9,
                    "exact_literal_rate": 1.0,
                    "output_tokens": 70.0,
                    "effective_total_tokens": 200.0,
                    "elapsed_ms": 800.0,
                },
                "sigil-a": {
                    "structured_expected_rate": 1.0,
                    "parse_rate": 1.0,
                    "repair_parse_rate": 1.0,
                    "mode_match_rate": 1.0,
                    "repair_mode_match_rate": 1.0,
                    "must_include_rate": 0.9,
                    "exact_literal_rate": 1.0,
                    "output_tokens": 80.0,
                    "effective_total_tokens": 240.0,
                    "elapsed_ms": 1200.0,
                },
            }
        }
        profile = SUGGEST_PROFILE.build_profile(
            summary,
            objective="efficiency",
            profile_name="efficiency_plain_ok",
            allow_plain_candidates=True,
        )
        self.assertEqual(profile["categories"]["debugging"], "baseline-terse")

    def test_task_granularity_profile_can_pick_different_variants_per_task(self) -> None:
        summary = {
            "task-a": {
                "baseline-terse": {
                    "structured_expected_rate": 0.0,
                    "parse_rate": 0.0,
                    "repair_parse_rate": 0.0,
                    "mode_match_rate": 0.0,
                    "repair_mode_match_rate": 0.0,
                    "must_include_rate": 0.8,
                    "exact_literal_rate": 1.0,
                    "output_tokens": 50.0,
                    "effective_total_tokens": 120.0,
                    "elapsed_ms": 500.0,
                },
                "sigil-a": {
                    "structured_expected_rate": 1.0,
                    "parse_rate": 1.0,
                    "repair_parse_rate": 1.0,
                    "mode_match_rate": 1.0,
                    "repair_mode_match_rate": 1.0,
                    "must_include_rate": 0.8,
                    "exact_literal_rate": 1.0,
                    "output_tokens": 60.0,
                    "effective_total_tokens": 150.0,
                    "elapsed_ms": 400.0,
                },
            },
            "task-b": {
                "baseline-terse": {
                    "structured_expected_rate": 0.0,
                    "parse_rate": 0.0,
                    "repair_parse_rate": 0.0,
                    "mode_match_rate": 0.0,
                    "repair_mode_match_rate": 0.0,
                    "must_include_rate": 0.5,
                    "exact_literal_rate": 0.75,
                    "output_tokens": 90.0,
                    "effective_total_tokens": 200.0,
                    "elapsed_ms": 800.0,
                },
                "sigil-b": {
                    "structured_expected_rate": 1.0,
                    "parse_rate": 1.0,
                    "repair_parse_rate": 1.0,
                    "mode_match_rate": 1.0,
                    "repair_mode_match_rate": 1.0,
                    "must_include_rate": 0.75,
                    "exact_literal_rate": 1.0,
                    "output_tokens": 40.0,
                    "effective_total_tokens": 110.0,
                    "elapsed_ms": 300.0,
                },
            },
        }
        profile = SUGGEST_PROFILE.build_profile(
            summary,
            objective="efficiency",
            profile_name="task_router_v1",
            allow_plain_candidates=True,
            granularity="task",
        )
        self.assertEqual(profile["tasks"]["task-a"], "baseline-terse")
        self.assertEqual(profile["tasks"]["task-b"], "sigil-b")


if __name__ == "__main__":
    unittest.main()
