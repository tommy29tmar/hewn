from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sigil.calibration import (
    baseline_multi_ir_extended_run_path,
    build_multi_ir_extended_profile_name,
    calibration_label,
    build_profile_name,
    default_anthropic_multi_ir_extended_jobs,
    default_anthropic_micro_jobs,
    default_gemini_multi_ir_extended_jobs,
    default_gemini_micro_jobs,
    default_openai_multi_ir_extended_jobs,
    default_openai_micro_jobs,
    load_profile,
    model_slug,
    multi_ir_extended_profile_path,
    multi_ir_extended_routed_run_path,
    profile_path,
    render_claude_code_md,
    routed_run_path,
)


class CalibrationTests(unittest.TestCase):
    def test_default_openai_micro_jobs_cover_all_categories(self) -> None:
        jobs = default_openai_micro_jobs()
        categories = {job.category for job in jobs}
        self.assertEqual(categories, {"debugging", "architecture", "code_review", "refactoring"})
        self.assertGreaterEqual(len(jobs), 12)

    def test_default_anthropic_micro_jobs_are_direct_only(self) -> None:
        jobs = default_anthropic_micro_jobs()
        self.assertEqual({job.category for job in jobs}, {"debugging", "architecture", "code_review", "refactoring"})
        self.assertTrue(all("wire-lite" not in job.prompt_family for job in jobs))
        self.assertTrue(any(job.prompt_family == "direct-minimal" for job in jobs))
        self.assertIn("capsule-mini", {job.prompt_family for job in jobs})

    def test_default_gemini_micro_jobs_include_wire_and_direct(self) -> None:
        jobs = default_gemini_micro_jobs()
        families = {job.prompt_family for job in jobs}
        self.assertIn("wire-lite", families)
        self.assertIn("direct-minimal", families)
        self.assertIn("direct-compact-v4", families)
        self.assertIn("slot-pack", families)

    def test_multi_ir_extended_jobs_cover_all_categories(self) -> None:
        self.assertEqual({job.category for job in default_openai_multi_ir_extended_jobs()}, {"debugging", "architecture", "code_review", "refactoring"})
        self.assertEqual({job.category for job in default_anthropic_multi_ir_extended_jobs()}, {"debugging", "architecture", "code_review", "refactoring"})
        self.assertEqual({job.category for job in default_gemini_multi_ir_extended_jobs()}, {"debugging", "architecture", "code_review", "refactoring"})
        self.assertIn("capsule-mini", {job.prompt_family for job in default_anthropic_multi_ir_extended_jobs()})
        self.assertIn("gemini-transfer", {job.prompt_family for job in default_anthropic_multi_ir_extended_jobs()})
        self.assertIn("gemini-nano", {job.prompt_family for job in default_gemini_multi_ir_extended_jobs()})
        self.assertIn("bridge", {job.prompt_family for job in default_openai_multi_ir_extended_jobs()})
        self.assertIn("bridge", {job.prompt_family for job in default_anthropic_multi_ir_extended_jobs()})
        self.assertIn("bridge", {job.prompt_family for job in default_gemini_multi_ir_extended_jobs()})
        self.assertIn("direct-compact-v4-cap72", {job.prompt_family for job in default_openai_multi_ir_extended_jobs()})
        self.assertIn("openai-gemini-nano", {job.prompt_family for job in default_openai_multi_ir_extended_jobs()})
        self.assertIn("claude-nano-cap56", {job.prompt_family for job in default_anthropic_multi_ir_extended_jobs()})
        self.assertIn("gemini-nano-cap64", {job.prompt_family for job in default_gemini_multi_ir_extended_jobs()})

    def test_model_slug_normalizes_identifier(self) -> None:
        self.assertEqual(model_slug("gpt-5.4-mini"), "gpt_5_4_mini")

    def test_build_profile_name(self) -> None:
        self.assertEqual(build_profile_name("gpt-5.4-mini", "efficiency"), "gpt_5_4_mini_micro_efficiency_router")

    def test_selective_calibration_helpers(self) -> None:
        self.assertEqual(calibration_label("efficiency", True), "selective_efficiency")
        self.assertEqual(
            build_profile_name("gpt-5.4-mini", "efficiency", True),
            "gpt_5_4_mini_micro_selective_efficiency_router",
        )
        self.assertEqual(
            profile_path("gpt-5.4-mini", "efficiency", Path("/tmp"), True),
            Path("/tmp/gpt_5_4_mini_micro_selective_efficiency_router.json"),
        )
        self.assertEqual(
            routed_run_path("gpt-5.4-mini", "efficiency", Path("/tmp"), True),
            Path("/tmp/gpt_5_4_mini_hybrid_micro_selective_efficiency.jsonl"),
        )
        self.assertEqual(
            baseline_multi_ir_extended_run_path("gpt-5.4-mini", Path("/tmp")),
            Path("/tmp/gpt_5_4_mini_baseline_hybrid_nano_extended.jsonl"),
        )
        self.assertEqual(
            build_multi_ir_extended_profile_name("gpt-5.4-mini", "efficiency", True),
            "gpt_5_4_mini_multi_ir_extended_selective_efficiency_router",
        )
        self.assertEqual(
            multi_ir_extended_profile_path("gpt-5.4-mini", "efficiency", Path("/tmp"), True),
            Path("/tmp/gpt_5_4_mini_multi_ir_extended_selective_efficiency_router.json"),
        )
        self.assertEqual(
            multi_ir_extended_routed_run_path("gpt-5.4-mini", "efficiency", Path("/tmp"), True),
            Path("/tmp/gpt_5_4_mini_hybrid_multi_ir_extended_selective_efficiency.jsonl"),
        )

    def test_render_claude_code_md_contains_routing(self) -> None:
        profile = {
            "name": "demo_profile",
            "categories": {
                "debugging": "sigil-debug-direct-compact",
                "architecture": "sigil-architecture-direct-compact",
                "code_review": "sigil-review-direct-compact",
                "refactoring": "sigil-refactor-direct-compact",
            },
        }
        rendered = render_claude_code_md(profile=profile, model="claude-sonnet-4-20250514")
        self.assertIn("demo_profile", rendered)
        self.assertIn("`debugging` -> `sigil-debug-direct-compact`", rendered)
        self.assertIn("Use normal human-language answers by default.", rendered)

    def test_load_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "profile.json"
            path.write_text(json.dumps({"name": "x", "categories": {}}), encoding="utf-8")
            loaded = load_profile(path)
            self.assertEqual(loaded["name"], "x")
