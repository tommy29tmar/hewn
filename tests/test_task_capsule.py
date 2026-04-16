from __future__ import annotations

import json
import unittest
from pathlib import Path

from sigil.metrics import approx_token_count
from sigil.task_capsule import build_capsule_task_row, build_task_capsule, load_jsonl


ROOT = Path(__file__).resolve().parents[1]


class TaskCapsuleTests(unittest.TestCase):
    def test_debug_capsule_preserves_critical_literals_and_is_shorter(self) -> None:
        task = load_jsonl(ROOT / "evals" / "tasks_debug.jsonl")[0]
        capsule = build_task_capsule(task)
        self.assertIn("[capsule v1 debugging]", capsule)
        self.assertIn('anchors: "<" | "401"', capsule)
        self.assertIn("authMiddleware", capsule)
        self.assertIn("401", capsule)
        self.assertLess(approx_token_count(capsule), approx_token_count(str(task["prompt"])))

    def test_review_capsule_preserves_header_and_context(self) -> None:
        task = load_jsonl(ROOT / "evals" / "tasks_review.jsonl")[0]
        capsule = build_task_capsule(task)
        self.assertIn("[capsule v1 review]", capsule)
        self.assertIn('"x-user-id"', capsule)
        self.assertIn("x-user-id", capsule)
        self.assertIn("public API gateway", capsule)

    def test_architecture_capsule_extracts_structured_facts(self) -> None:
        task = load_jsonl(ROOT / "evals" / "tasks_architecture.jsonl")[0]
        capsule = build_task_capsule(task)
        self.assertIn("team: 6", capsule)
        self.assertIn('deadline: "4 months"', capsule)
        self.assertIn('store: "PostgreSQL"', capsule)

    def test_refactor_capsule_extracts_target_and_error_path(self) -> None:
        task = load_jsonl(ROOT / "evals" / "tasks_refactor.jsonl")[0]
        capsule = build_task_capsule(task)
        self.assertIn("target: loadUser", capsule)
        self.assertIn('error_path: "next(err)"', capsule)

    def test_build_capsule_task_row_marks_capsule(self) -> None:
        task = load_jsonl(ROOT / "evals" / "tasks_architecture.jsonl")[0]
        row = build_capsule_task_row(task)
        self.assertEqual(row["capsule"], "v1")
        self.assertNotEqual(row["prompt"], task["prompt"])
        json.dumps(row)

    def test_micro_capsule_is_shorter_for_debug(self) -> None:
        task = load_jsonl(ROOT / "evals" / "tasks_debug.jsonl")[0]
        normal = build_task_capsule(task)
        micro = build_task_capsule(task, style="micro")
        self.assertIn("[capsule micro debugging]", micro)
        self.assertLess(approx_token_count(micro), approx_token_count(normal))

    def test_micro_refactor_capsule_preserves_target_and_next_err(self) -> None:
        task = load_jsonl(ROOT / "evals" / "tasks_refactor.jsonl")[0]
        micro = build_task_capsule(task, style="micro")
        self.assertIn("target: loadUser", micro)
        self.assertIn('"next(err)"', micro)

    def test_nano_capsule_is_shorter_than_micro(self) -> None:
        task = load_jsonl(ROOT / "evals" / "tasks_review.jsonl")[0]
        micro = build_task_capsule(task, style="micro")
        nano = build_task_capsule(task, style="nano")
        self.assertIn("[r]", nano)
        self.assertIn("header", nano)
        self.assertLess(approx_token_count(nano), approx_token_count(micro))

    def test_nano_refactor_capsule_keeps_target_and_literals(self) -> None:
        task = load_jsonl(ROOT / "evals" / "tasks_refactor.jsonl")[0]
        nano = build_task_capsule(task, style="nano")
        self.assertIn("loadUser", nano)
        self.assertIn("next(err)", nano)

    def test_bridge_architecture_capsule_keeps_compact_structure(self) -> None:
        task = load_jsonl(ROOT / "evals" / "tasks_architecture_micro_extended.jsonl")[1]
        bridge = build_task_capsule(task, style="bridge")
        micro = build_task_capsule(task, style="micro")
        self.assertIn("[a2]", bridge)
        self.assertIn("f(", bridge)
        self.assertIn('"6 weeks"', bridge)
        self.assertLess(approx_token_count(bridge), approx_token_count(micro))

    def test_bridge_debug_capsule_keeps_rule_and_focus(self) -> None:
        task = load_jsonl(ROOT / "evals" / "tasks_debug_micro_extended.jsonl")[0]
        bridge = build_task_capsule(task, style="bridge")
        self.assertIn("[d2]", bridge)
        self.assertIn("r(", bridge)
        self.assertIn("f(", bridge)


if __name__ == "__main__":
    unittest.main()
