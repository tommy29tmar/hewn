from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "evals" / "run_gemini.py"
SPEC = importlib.util.spec_from_file_location("sigil_eval_run_gemini", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
RUN_GEMINI = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUN_GEMINI
SPEC.loader.exec_module(RUN_GEMINI)


class RunGeminiTests(unittest.TestCase):
    def test_should_retry_http_status(self) -> None:
        self.assertTrue(RUN_GEMINI.should_retry_http_status(503))
        self.assertFalse(RUN_GEMINI.should_retry_http_status(400))

    def test_build_payload_for_direct_sigil(self) -> None:
        payload = RUN_GEMINI.build_payload(
            task_prompt="Review this patch.",
            instructions="Be terse.",
            max_output_tokens=200,
            transport="sigil",
            thinking_budget=0,
            stop_sequences=["\n[AUDIT]"],
        )
        self.assertEqual(payload["contents"][0]["parts"][0]["text"], "Review this patch.")
        self.assertEqual(payload["generationConfig"]["thinkingConfig"]["thinkingBudget"], 0)
        self.assertNotIn("responseSchema", payload["generationConfig"])
        self.assertIn("stopSequences", payload["generationConfig"])
        self.assertIn("\n[AUDIT]", payload["generationConfig"]["stopSequences"])
        self.assertIn("systemInstruction", payload)

    def test_build_payload_for_schema_transport(self) -> None:
        payload = RUN_GEMINI.build_payload(
            task_prompt="Review this patch.",
            instructions="Return compact json.",
            max_output_tokens=200,
            transport="schema-debug_wire_lite",
            thinking_budget=None,
        )
        self.assertEqual(payload["generationConfig"]["responseMimeType"], "application/json")
        self.assertIn("responseSchema", payload["generationConfig"])

    def test_build_payload_for_packed_transport_drops_boolean_items_false(self) -> None:
        payload = RUN_GEMINI.build_payload(
            task_prompt="Debug this middleware.",
            instructions="Return compact json.",
            max_output_tokens=180,
            transport="schema-debug_pack",
            thinking_budget=0,
        )
        schema = payload["generationConfig"]["responseSchema"]
        packed_array = schema["properties"]["d"]
        self.assertIn("prefixItems", packed_array)
        self.assertNotIn("items", packed_array)

    def test_build_payload_with_cached_content_omits_system_instruction(self) -> None:
        payload = RUN_GEMINI.build_payload(
            task_prompt="Dynamic task suffix.",
            instructions="Return compact json.",
            max_output_tokens=180,
            transport="sigil",
            thinking_budget=0,
            cached_content_name="cachedContents/demo123",
        )
        self.assertEqual(payload["cachedContent"], "cachedContents/demo123")
        self.assertNotIn("systemInstruction", payload)

    def test_build_payload_can_disable_stop_sequences(self) -> None:
        payload = RUN_GEMINI.build_payload(
            task_prompt="Dynamic task suffix.",
            instructions="Return compact json.",
            max_output_tokens=180,
            transport="plain",
            thinking_budget=0,
            stop_sequences=[],
        )
        self.assertNotIn("stopSequences", payload["generationConfig"])

    def test_build_cache_payload(self) -> None:
        payload = RUN_GEMINI.build_cache_payload(
            model="gemini-2.5-flash",
            instructions="Return compact json.",
            cache_prefix="Long static project context.",
            ttl="3600s",
            display_name="sigil-eval-demo",
        )
        self.assertEqual(payload["model"], "models/gemini-2.5-flash")
        self.assertEqual(payload["ttl"], "3600s")
        self.assertEqual(payload["displayName"], "sigil-eval-demo")
        self.assertIn("systemInstruction", payload)
        self.assertEqual(payload["contents"][0]["parts"][0]["text"], "Long static project context.")

    def test_extract_output_text(self) -> None:
        response = {"candidates": [{"content": {"parts": [{"text": "@sigil v0 hybrid"}]}}]}
        self.assertEqual(RUN_GEMINI.extract_output_text(response), "@sigil v0 hybrid")

    def test_extract_usage(self) -> None:
        usage = RUN_GEMINI.extract_usage(
            {
                "usageMetadata": {
                    "promptTokenCount": 100,
                    "candidatesTokenCount": 30,
                    "totalTokenCount": 150,
                    "thoughtsTokenCount": 20,
                }
            }
        )
        self.assertEqual(usage["input_tokens"], 100)
        self.assertEqual(usage["output_tokens"], 30)
        self.assertEqual(usage["total_tokens"], 150)
        self.assertEqual(usage["reasoning_tokens"], 20)
