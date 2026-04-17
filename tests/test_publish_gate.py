"""Publish-gate tests: coverage, truncation, sentinel row rejection."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "publish_gate.py"
SPEC = importlib.util.spec_from_file_location("flint_publish_gate", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
PUBLISH_GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PUBLISH_GATE
SPEC.loader.exec_module(PUBLISH_GATE)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def _tasks_file(path: Path, ids: list[str]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for tid in ids:
            f.write(json.dumps({"id": tid}) + "\n")


class PublishGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.cell = self.tmp / "cell.jsonl"
        self.tasks = self.tmp / "tasks.jsonl"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_clean_cell_passes(self) -> None:
        _tasks_file(self.tasks, ["a", "b"])
        _write_jsonl(
            self.cell,
            [
                {"task_id": "a", "content": "ok", "status": "end_turn"},
                {"task_id": "b", "content": "ok", "status": "end_turn"},
            ],
        )
        ok, problems = PUBLISH_GATE.check_cell(self.cell, self.tasks)
        self.assertTrue(ok, problems)

    def test_missing_task_fails(self) -> None:
        _tasks_file(self.tasks, ["a", "b"])
        _write_jsonl(self.cell, [{"task_id": "a", "content": "ok"}])
        ok, problems = PUBLISH_GATE.check_cell(self.cell, self.tasks)
        self.assertFalse(ok)
        self.assertTrue(any("missing" in p for p in problems))

    def test_truncation_fails(self) -> None:
        _tasks_file(self.tasks, ["a"])
        _write_jsonl(self.cell, [{"task_id": "a", "content": "partial", "status": "max_tokens"}])
        ok, problems = PUBLISH_GATE.check_cell(self.cell, self.tasks)
        self.assertFalse(ok)
        self.assertTrue(any("max_tokens" in p for p in problems))

if __name__ == "__main__":
    unittest.main()
