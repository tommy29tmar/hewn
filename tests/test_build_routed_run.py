from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "evals" / "build_routed_run.py"
SPEC = importlib.util.spec_from_file_location("sigil_eval_build_routed_run", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
BUILD_ROUTED_RUN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BUILD_ROUTED_RUN
SPEC.loader.exec_module(BUILD_ROUTED_RUN)


class BuildRoutedRunTests(unittest.TestCase):
    def test_main_can_route_to_baseline_variant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            tasks = tmp_path / "tasks.jsonl"
            profile = tmp_path / "profile.json"
            source = tmp_path / "source.jsonl"
            baseline = tmp_path / "baseline.jsonl"
            out = tmp_path / "out.jsonl"

            tasks.write_text(json.dumps({"id": "debug-task", "category": "debugging"}) + "\n", encoding="utf-8")
            profile.write_text(
                json.dumps(
                    {
                        "name": "mixed-router",
                        "categories": {"debugging": "baseline-terse"},
                    }
                ),
                encoding="utf-8",
            )
            source.write_text(
                json.dumps({"task_id": "debug-task", "variant": "sigil-debug", "content": "@flint v0 hybrid\nG: fix(auth)"}) + "\n",
                encoding="utf-8",
            )
            baseline.write_text(
                json.dumps({"task_id": "debug-task", "variant": "baseline-terse", "content": "Use plain baseline output."}) + "\n",
                encoding="utf-8",
            )

            exit_code = BUILD_ROUTED_RUN.main(
                [
                    str(tasks),
                    str(profile),
                    str(out),
                    "--source-run",
                    str(source),
                    "--baseline-run",
                    str(baseline),
                ]
            )
            self.assertEqual(exit_code, 0)
            rows = BUILD_ROUTED_RUN.load_jsonl(out)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["variant"], "baseline-terse")
            self.assertEqual(rows[1]["variant"], "sigil-routed")
            self.assertEqual(rows[1]["policy_source_variant"], "baseline-terse")
            self.assertEqual(rows[1]["content"], "Use plain baseline output.")

    def test_main_prefers_task_override_over_category_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            tasks = tmp_path / "tasks.jsonl"
            profile = tmp_path / "profile.json"
            source = tmp_path / "source.jsonl"
            out = tmp_path / "out.jsonl"

            tasks.write_text(
                "".join(
                    json.dumps(row) + "\n"
                    for row in (
                        {"id": "task-a", "category": "debugging"},
                        {"id": "task-b", "category": "debugging"},
                    )
                ),
                encoding="utf-8",
            )
            profile.write_text(
                json.dumps(
                    {
                        "name": "task-router",
                        "categories": {"debugging": "sigil-debug"},
                        "tasks": {"task-b": "sigil-alt"},
                    }
                ),
                encoding="utf-8",
            )
            source.write_text(
                "".join(
                    json.dumps(row) + "\n"
                    for row in (
                        {"task_id": "task-a", "variant": "sigil-debug", "content": "@flint v0 hybrid\nG: a"},
                        {"task_id": "task-b", "variant": "sigil-debug", "content": "@flint v0 hybrid\nG: b-default"},
                        {"task_id": "task-b", "variant": "sigil-alt", "content": "@flint v0 hybrid\nG: b-alt"},
                    )
                ),
                encoding="utf-8",
            )

            exit_code = BUILD_ROUTED_RUN.main([str(tasks), str(profile), str(out), "--source-run", str(source)])
            self.assertEqual(exit_code, 0)
            rows = BUILD_ROUTED_RUN.load_jsonl(out)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["policy_source_variant"], "sigil-debug")
            self.assertEqual(rows[1]["policy_source_variant"], "sigil-alt")
            self.assertIn("b-alt", rows[1]["content"])


if __name__ == "__main__":
    unittest.main()
