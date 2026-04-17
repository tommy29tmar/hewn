from __future__ import annotations

import unittest
from pathlib import Path

from flint.context_prefix import compile_context_layers, compile_context_prefix, parse_handbook_sections
from flint.metrics import approx_token_count


ROOT = Path(__file__).resolve().parents[1]


class ContextPrefixTests(unittest.TestCase):
    def test_parse_handbook_sections_extracts_known_headings(self) -> None:
        source = (ROOT / "evals" / "prefixes" / "service_context_v1.txt").read_text(encoding="utf-8")
        sections = parse_handbook_sections(source)
        self.assertIn("product snapshot", sections)
        self.assertIn("authentication and session rules", sections)
        self.assertIn("what not to do", sections)

    def test_cacheable_prefix_is_shorter_than_raw_and_keeps_key_literals(self) -> None:
        source = (ROOT / "evals" / "prefixes" / "service_context_v1.txt").read_text(encoding="utf-8")
        compiled = compile_context_prefix(source, category="debugging", style="cacheable")
        self.assertIn("[ctx cacheable debugging]", compiled)
        self.assertIn("`x-user-id`", compiled)
        self.assertIn("`401`", compiled)
        self.assertLess(approx_token_count(compiled), approx_token_count(source))
        self.assertGreater(approx_token_count(compiled), 500)

    def test_focused_prefix_is_shorter_than_cacheable(self) -> None:
        source = (ROOT / "evals" / "prefixes" / "service_context_v1.txt").read_text(encoding="utf-8")
        cacheable = compile_context_prefix(source, category="code_review", style="cacheable")
        focused = compile_context_prefix(source, category="code_review", style="focused")
        self.assertIn("[ctx focused code_review]", focused)
        self.assertLess(approx_token_count(focused), approx_token_count(cacheable))
        self.assertIn("spoof", focused.lower())

    def test_targeted_prefix_is_shorter_than_focused_and_keeps_anchors(self) -> None:
        source = (ROOT / "evals" / "prefixes" / "service_context_v1.txt").read_text(encoding="utf-8")
        task = {
            "id": "t1",
            "category": "debugging",
            "prompt": "Fix auth expiry bug around x-user-id and 401 boundary with next(err).",
            "exact_literals": ["x-user-id", "401", "next(err)"],
            "must_include": ["auth", "expiry", "boundary"],
        }
        focused = compile_context_prefix(source, category="debugging", style="focused", task=task)
        targeted = compile_context_prefix(source, category="debugging", style="targeted", task=task)
        self.assertIn("[ctx targeted debugging]", targeted)
        self.assertIn('anchors: "x-user-id" | "401" | "next(err)"', targeted)
        self.assertIn("`401`", targeted)
        self.assertIn("`x-user-id`", targeted)
        self.assertLess(approx_token_count(targeted), approx_token_count(focused))

    def test_targeted_prefix_for_architecture_keeps_deadline_and_store(self) -> None:
        source = (ROOT / "evals" / "prefixes" / "service_context_v1.txt").read_text(encoding="utf-8")
        task = {
            "id": "a1",
            "category": "architecture",
            "prompt": "Recommend the default architecture for a team shipping in 4 months using PostgreSQL.",
            "exact_literals": ["PostgreSQL", "4 months"],
            "must_include": ["modular monolith", "low ops"],
        }
        targeted = compile_context_prefix(source, category="architecture", style="targeted", task=task)
        self.assertIn('"PostgreSQL"', targeted)
        self.assertIn('"4 months"', targeted)
        self.assertIn("PostgreSQL is the default SoR.", targeted)

    def test_needle_prefix_is_shorter_than_targeted_and_keeps_anchors(self) -> None:
        source = (ROOT / "evals" / "prefixes" / "service_context_v1.txt").read_text(encoding="utf-8")
        task = {
            "id": "t2",
            "category": "debugging",
            "prompt": "Fix auth expiry bug around x-user-id and 401 boundary with next(err).",
            "exact_literals": ["x-user-id", "401", "next(err)"],
            "must_include": ["auth", "expiry", "boundary"],
        }
        targeted = compile_context_prefix(source, category="debugging", style="targeted", task=task)
        needle = compile_context_prefix(source, category="debugging", style="needle", task=task)
        self.assertIn("[ctx needle debugging]", needle)
        self.assertIn('anchors: "x-user-id" | "401" | "next(err)"', needle)
        self.assertLess(approx_token_count(needle), approx_token_count(targeted))

    def test_delta_prefix_is_shorter_than_needle_and_keeps_anchors(self) -> None:
        source = (ROOT / "evals" / "prefixes" / "service_context_v1.txt").read_text(encoding="utf-8")
        task = {
            "id": "t3",
            "category": "debugging",
            "prompt": "Fix auth expiry bug around x-user-id and 401 boundary with next(err).",
            "exact_literals": ["x-user-id", "401", "next(err)"],
            "must_include": ["auth", "expiry", "boundary"],
        }
        needle = compile_context_prefix(source, category="debugging", style="needle", task=task)
        delta = compile_context_prefix(source, category="debugging", style="delta", task=task)
        self.assertIn("[ctx delta debugging]", delta)
        self.assertIn('anchors: "x-user-id" | "401" | "next(err)"', delta)
        self.assertLess(approx_token_count(delta), approx_token_count(needle))

    def test_context_layers_keep_shared_prefix_and_task_overlay(self) -> None:
        source = (ROOT / "evals" / "prefixes" / "service_context_v1.txt").read_text(encoding="utf-8")
        debug_task = {
            "id": "t1",
            "category": "debugging",
            "prompt": "Fix auth expiry bug around x-user-id and 401 boundary.",
            "exact_literals": ["x-user-id", "401"],
            "must_include": ["auth", "expiry"],
        }
        architecture_task = {
            "id": "a1",
            "category": "architecture",
            "prompt": "Choose architecture with PostgreSQL and 4 months deadline.",
            "exact_literals": ["PostgreSQL", "4 months"],
            "must_include": ["modular monolith", "low ops"],
        }
        debug_shared, debug_overlay = compile_context_layers(source, category="debugging", task=debug_task)
        arch_shared, arch_overlay = compile_context_layers(source, category="architecture", task=architecture_task)
        self.assertEqual(debug_shared, arch_shared)
        self.assertIn("[ctx cacheable shared]", debug_shared)
        self.assertIn("[ctx targeted debugging]", debug_overlay)
        self.assertIn("[ctx targeted architecture]", arch_overlay)
        self.assertNotEqual(debug_overlay, arch_overlay)

    def test_context_layers_support_delta_overlay(self) -> None:
        source = (ROOT / "evals" / "prefixes" / "service_context_v1.txt").read_text(encoding="utf-8")
        debug_task = {
            "id": "t4",
            "category": "debugging",
            "prompt": "Fix auth expiry bug around x-user-id and 401 boundary.",
            "exact_literals": ["x-user-id", "401"],
            "must_include": ["auth", "expiry"],
        }
        shared, overlay = compile_context_layers(source, category="debugging", task=debug_task, task_style="delta")
        self.assertIn("[ctx cacheable shared]", shared)
        self.assertIn("[ctx delta debugging]", overlay)
        self.assertNotIn("title:", overlay)
        self.assertNotIn("scope:", overlay)


if __name__ == "__main__":
    unittest.main()
