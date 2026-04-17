"""Tests for src/flint/routing.py and the `flint routing recommend` CLI."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from flint.cli import main as cli_main
from flint.routing import load_profile, pick_variant


class PickVariantTests(unittest.TestCase):
    def _profile(self) -> dict:
        return {
            "name": "test",
            "objective": "efficiency",
            "granularity": "task",
            "categories": {"debugging": "sigil-debug", "architecture": "sigil-arch"},
            "tasks": {"debug-webhook-ts-skew": "sigil-debug-micro"},
        }

    def test_task_override_beats_category(self) -> None:
        profile = self._profile()
        pick = pick_variant(profile, task_id="debug-webhook-ts-skew", category="debugging")
        self.assertEqual(pick, "sigil-debug-micro")

    def test_category_fallback_when_no_task_match(self) -> None:
        profile = self._profile()
        pick = pick_variant(profile, task_id="unknown-task", category="architecture")
        self.assertEqual(pick, "sigil-arch")

    def test_returns_none_when_no_match(self) -> None:
        profile = self._profile()
        self.assertIsNone(pick_variant(profile, task_id="none", category="none"))

    def test_category_only_profile(self) -> None:
        profile = {"categories": {"refactoring": "sigil-ref"}}
        self.assertEqual(pick_variant(profile, category="refactoring"), "sigil-ref")
        self.assertIsNone(pick_variant(profile, category="debugging"))

    def test_task_only_profile(self) -> None:
        profile = {"tasks": {"t1": "v1"}}
        self.assertEqual(pick_variant(profile, task_id="t1"), "v1")
        self.assertIsNone(pick_variant(profile, task_id="t2"))


class LoadProfileTests(unittest.TestCase):
    def test_load_valid_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.json"
            path.write_text(json.dumps({"categories": {"x": "y"}}))
            profile = load_profile(path)
            self.assertEqual(profile["categories"], {"x": "y"})

    def test_rejects_empty_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.json"
            path.write_text(json.dumps({"name": "x"}))
            with self.assertRaises(ValueError):
                load_profile(path)

    def test_rejects_non_dict_categories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.json"
            path.write_text(json.dumps({"categories": ["a", "b"]}))
            with self.assertRaises(ValueError):
                load_profile(path)


class CliRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.profile = self.tmp / "profile.json"
        self.profile.write_text(
            json.dumps(
                {
                    "categories": {"debugging": "sigil-debug"},
                    "tasks": {"t1": "sigil-micro"},
                }
            )
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_recommend_category_hit(self) -> None:
        rc = cli_main(["routing", "recommend", "--profile", str(self.profile), "--category", "debugging"])
        self.assertEqual(rc, 0)

    def test_recommend_task_override(self) -> None:
        rc = cli_main(["routing", "recommend", "--profile", str(self.profile), "--task-id", "t1", "--category", "debugging"])
        self.assertEqual(rc, 0)

    def test_recommend_miss_returns_1(self) -> None:
        rc = cli_main(["routing", "recommend", "--profile", str(self.profile), "--category", "unknown"])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
