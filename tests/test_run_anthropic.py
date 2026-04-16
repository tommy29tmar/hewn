from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "evals" / "run_anthropic.py"
SPEC = importlib.util.spec_from_file_location("sigil_eval_run_anthropic", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
RUN_ANTHROPIC = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUN_ANTHROPIC
SPEC.loader.exec_module(RUN_ANTHROPIC)


class RunAnthropicTests(unittest.TestCase):
    def test_should_retry_http_status(self) -> None:
        self.assertTrue(RUN_ANTHROPIC.should_retry_http_status(503))
        self.assertFalse(RUN_ANTHROPIC.should_retry_http_status(400))

    def test_build_payload_without_thinking(self) -> None:
        payload = RUN_ANTHROPIC.build_payload(
            model="claude-sonnet-4-20250514",
            task_prompt="Review this patch.",
            instructions="Be terse.",
            max_output_tokens=200,
            thinking_budget=None,
            cache_system_prompt=False,
        )
        self.assertEqual(payload["model"], "claude-sonnet-4-20250514")
        self.assertEqual(payload["messages"][0]["content"][0]["text"], "Review this patch.")
        self.assertNotIn("thinking", payload)
        self.assertNotIn("stop_sequences", payload)

    def test_build_payload_with_thinking_and_cache(self) -> None:
        payload = RUN_ANTHROPIC.build_payload(
            model="claude-sonnet-4-20250514",
            task_prompt="Review this patch.",
            instructions="Be terse.",
            max_output_tokens=200,
            thinking_budget=512,
            cache_system_prompt=True,
        )
        self.assertEqual(payload["thinking"]["budget_tokens"], 512)
        self.assertEqual(payload["system"][0]["cache_control"]["type"], "ephemeral")

    def test_build_payload_with_cached_task_prefix(self) -> None:
        payload = RUN_ANTHROPIC.build_payload(
            model="claude-sonnet-4-20250514",
            task_prompt="suffix only",
            instructions="Be terse.",
            max_output_tokens=200,
            thinking_budget=None,
            cache_system_prompt=False,
            cache_prefix="[ctx cacheable]\nauth: keep `401`",
        )
        self.assertEqual(len(payload["system"]), 2)
        self.assertEqual(payload["system"][1]["cache_control"]["type"], "ephemeral")
        self.assertEqual(payload["messages"][0]["content"][0]["text"], "suffix only")

    def test_build_payload_with_stop_sequences(self) -> None:
        payload = RUN_ANTHROPIC.build_payload(
            model="claude-sonnet-4-20250514",
            task_prompt="Review this patch.",
            instructions="Be terse.",
            max_output_tokens=200,
            thinking_budget=None,
            cache_system_prompt=False,
            stop_sequences=["\n[AUDIT]"],
        )
        self.assertEqual(payload["stop_sequences"], ["\n[AUDIT]"])

    def test_extract_output_text(self) -> None:
        response = {"content": [{"type": "thinking", "thinking": "hidden"}, {"type": "text", "text": "@sigil v0 hybrid"}]}
        self.assertEqual(RUN_ANTHROPIC.extract_output_text(response), "@sigil v0 hybrid")

    def test_extract_usage_includes_cache_reads(self) -> None:
        usage = RUN_ANTHROPIC.extract_usage(
            {
                "usage": {
                    "input_tokens": 100,
                    "cache_creation_input_tokens": 10,
                    "cache_read_input_tokens": 20,
                    "output_tokens": 40,
                }
            }
        )
        self.assertEqual(usage["input_tokens"], 130)
        self.assertEqual(usage["cached_tokens"], 20)
        self.assertEqual(usage["total_tokens"], 170)
