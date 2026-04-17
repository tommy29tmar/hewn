from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

from flint.cache import cache_eligibility, resolve_cache_policy


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "evals" / "cache_report.py"
SPEC = importlib.util.spec_from_file_location("sigil_eval_cache_report", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
CACHE_REPORT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CACHE_REPORT
SPEC.loader.exec_module(CACHE_REPORT)


class CacheTests(unittest.TestCase):
    def test_openai_policy_uses_1024_threshold(self) -> None:
        policy = resolve_cache_policy("openai", "gpt-5.4-mini")
        self.assertEqual(policy.minimum_input_tokens, 1024)

    def test_anthropic_sonnet_vs_haiku_thresholds(self) -> None:
        sonnet = resolve_cache_policy("anthropic", "claude-sonnet-4-20250514")
        haiku = resolve_cache_policy("anthropic", "claude-haiku-3.5")
        self.assertEqual(sonnet.minimum_input_tokens, 1024)
        self.assertEqual(haiku.minimum_input_tokens, 2048)

    def test_anthropic_newer_thresholds(self) -> None:
        sonnet = resolve_cache_policy("anthropic", "claude-sonnet-4.6")
        opus = resolve_cache_policy("anthropic", "claude-opus-4.6")
        self.assertEqual(sonnet.minimum_input_tokens, 2048)
        self.assertEqual(opus.minimum_input_tokens, 4096)

    def test_gemini_flash_threshold(self) -> None:
        policy = resolve_cache_policy("gemini", "gemini-2.5-flash")
        self.assertEqual(policy.minimum_input_tokens, 1024)

    def test_cache_eligibility_reports_gap_and_ratio(self) -> None:
        policy = resolve_cache_policy("openai", "gpt-5.4")
        report = cache_eligibility(256, policy)
        self.assertFalse(report["eligible"])
        self.assertEqual(report["threshold_gap_tokens"], -768)
        self.assertEqual(report["threshold_ratio"], 0.25)

    def test_cache_report_marks_small_runs_as_too_small(self) -> None:
        policy = resolve_cache_policy("openai", "gpt-5.4-mini")
        summary = CACHE_REPORT.summarize_variant(
            [
                {"usage": {"input_tokens": 150, "cached_tokens": 0}},
                {"usage": {"input_tokens": 210, "cached_tokens": 0}},
            ],
            policy,
        )
        self.assertEqual(summary["verdict"], "too_small_for_cache")
        self.assertEqual(summary["eligible_rate"], 0.0)

    def test_cache_report_marks_hits_as_active(self) -> None:
        policy = resolve_cache_policy("openai", "gpt-5.4-mini")
        summary = CACHE_REPORT.summarize_variant(
            [
                {"usage": {"input_tokens": 1300, "cached_tokens": 500}},
                {"usage": {"input_tokens": 1500, "cached_tokens": 800}},
            ],
            policy,
        )
        self.assertEqual(summary["verdict"], "cache_active")
        self.assertEqual(summary["eligible_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
