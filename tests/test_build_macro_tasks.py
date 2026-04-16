from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "evals" / "build_macro_tasks.py"
SPEC = importlib.util.spec_from_file_location("sigil_eval_build_macro_tasks", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
BUILD_MACRO_TASKS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BUILD_MACRO_TASKS
SPEC.loader.exec_module(BUILD_MACRO_TASKS)


class BuildMacroTasksTests(unittest.TestCase):
    def test_build_macro_tasks_adds_prefix_and_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "tasks.jsonl"
            prefix = root / "prefix.txt"
            out = root / "macro.jsonl"
            source.write_text(
                json.dumps({"id": "t1", "prompt": "Fix the bug.", "category": "debugging", "mode": "hybrid"}) + "\n",
                encoding="utf-8",
            )
            prefix.write_text("Stable project context.", encoding="utf-8")
            exit_code = BUILD_MACRO_TASKS.main([str(source), str(prefix), str(out)])
            self.assertEqual(exit_code, 0)
            row = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row["prompt_suffix"], "Fix the bug.")
            self.assertEqual(row["cache_prefix"], "Stable project context.")
            self.assertIn("Stable project context.", row["prompt"])
            self.assertIn("[Task]", row["prompt"])
            self.assertEqual(row["benchmark_scale"], "macro")


if __name__ == "__main__":
    unittest.main()
