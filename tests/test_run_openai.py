from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

from flint.normalize import normalize_document_text
from flint.parser import parse_document


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "evals" / "run_openai.py"
SPEC = importlib.util.spec_from_file_location("sigil_eval_run_openai", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
RUN_OPENAI = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUN_OPENAI
SPEC.loader.exec_module(RUN_OPENAI)


class RunOpenAITests(unittest.TestCase):
    def test_should_retry_http_status(self) -> None:
        self.assertTrue(RUN_OPENAI.should_retry_http_status(503))
        self.assertFalse(RUN_OPENAI.should_retry_http_status(400))

    def test_parse_env_line(self) -> None:
        self.assertEqual(RUN_OPENAI.parse_env_line("OPENAI_API_KEY=abc"), ("OPENAI_API_KEY", "abc"))
        self.assertEqual(RUN_OPENAI.parse_env_line("export OPENAI_BASE_URL='https://example.test/v1'"), ("OPENAI_BASE_URL", "https://example.test/v1"))
        self.assertIsNone(RUN_OPENAI.parse_env_line("# comment"))

    def test_parse_variant_with_kind(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-hybrid@structured=prompts/hybrid_strict.txt")
        self.assertEqual(variant.name, "sigil-hybrid")
        self.assertTrue(variant.structured_expected)
        self.assertEqual(variant.transport, "structured")

    def test_parse_variant_with_direct_sigil_kind(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-debug-direct@sigil=prompts/debug_direct_micro.txt")
        self.assertEqual(variant.transport, "sigil")
        self.assertTrue(variant.structured_expected)

    def test_parse_variant_with_schema_transport(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-hybrid@schema-hybrid=prompts/hybrid_schema.txt")
        self.assertEqual(variant.transport, "schema-hybrid")
        self.assertTrue(variant.structured_expected)

    def test_parse_variant_with_draft2schema_transport(self) -> None:
        variant = RUN_OPENAI.parse_variant(
            "sigil-debug-d2s@draft2schema-debug_hybrid=prompts/hybrid_strict.txt::prompts/debug_hybrid_schema.txt"
        )
        self.assertEqual(variant.transport, "draft2schema-debug_hybrid")
        self.assertTrue(variant.structured_expected)
        self.assertIsNotNone(variant.draft_prompt_path)

    def test_build_payload_includes_reasoning_and_verbosity(self) -> None:
        payload = RUN_OPENAI.build_payload(
            model="gpt-5.2",
            task_prompt="Review this bug.",
            instructions="Be concise.",
            max_output_tokens=400,
            reasoning_effort="medium",
            reasoning_summary="concise",
            verbosity="low",
            text_format=None,
            prompt_cache_key=None,
            prompt_cache_retention=None,
        )
        self.assertEqual(payload["model"], "gpt-5.2")
        self.assertEqual(payload["reasoning"]["effort"], "medium")
        self.assertEqual(payload["reasoning"]["summary"], "concise")
        self.assertEqual(payload["text"]["verbosity"], "low")

    def test_extract_output_text_prefers_top_level_field(self) -> None:
        response = {"output_text": "@flint v0 hybrid\nG: fix(auth)"}
        self.assertEqual(RUN_OPENAI.extract_output_text(response), "@flint v0 hybrid\nG: fix(auth)")

    def test_extract_usage_reads_reasoning_tokens(self) -> None:
        response = {
            "usage": {
                "input_tokens": 120,
                "output_tokens": 40,
                "total_tokens": 180,
                "output_tokens_details": {
                    "reasoning_tokens": 20,
                },
            }
        }
        usage = RUN_OPENAI.extract_usage(response)
        self.assertEqual(usage["input_tokens"], 120)
        self.assertEqual(usage["output_tokens"], 40)
        self.assertEqual(usage["total_tokens"], 180)
        self.assertEqual(usage["reasoning_tokens"], 20)

    def test_normalize_document_text_wraps_await_identifier(self) -> None:
        text = "@flint v0 hybrid\nP: try(await db_findUser) → next(err)\n[AUDIT]\nshort\n"
        normalized = normalize_document_text(text)
        self.assertIn("await(db_findUser)", normalized)

    def test_decode_variant_output_repairs_headerless_gemini_nano_architecture(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-architecture-gemini-nano@sigil=prompts/architecture_direct_sigil_gemini_nano.txt")
        response = {
            "output_text": "G: post_release\nC: 4 months\nP: PostgreSQL\nV: modular_monolith\nA: team, deadline, low_ops, fast_ship"
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("@flint v0 hybrid", content)
        self.assertIn("A: team ∧ deadline ∧ low_ops ∧ fast_ship", content)

    def test_decode_variant_output_repairs_headerless_gemini_nano_refactor(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-refactor-gemini-nano@sigil=prompts/refactor_direct_sigil_gemini_nano.txt")
        response = {
            "output_text": "G: `async`\nC: `await`\nP: `next(err)`\nV: target\nA: same_order"
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("@flint v0 hybrid", content)
        self.assertIn("G: async", content)
        self.assertIn("C: await", content)

    def test_decode_variant_output_uses_task_category_when_variant_is_generic(self) -> None:
        variant = RUN_OPENAI.parse_variant("current@sigil=integrations/claude-code/flint_system_prompt.txt")
        response = {
            "output_text": (
                "@flint v0 hybrid\n"
                "G: modular_monolith\n"
                'C: team=9 ∧ ddl="12 weeks" ∧ store="PostgreSQL" ∧ ops=platform_plus_sec ∧ traffic=steady\n'
                "P: modular_boundaries ∧ shared_pg\n"
                "V: compliance_ready\n"
                "A: defer_microservices\n"
            )
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response, task_category="architecture")
        self.assertIn('team(9)', content)
        self.assertIn('ddl("12 weeks")', content)
        self.assertIn("[AUDIT]", content)

    def test_decode_variant_output_renders_schema_payload(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-hybrid@schema-hybrid=prompts/hybrid_schema.txt")
        response = {
            "output_text": '{"mode":"hybrid","codebook":[],"goal":"fix(auth_middleware)","constraints":["backcompat","security"],"has_hypothesis":false,"hypothesis_left":"","hypothesis_right":"","plan":["add(test_boundary)"],"verification":["unit"],"risks":["auth_regression"],"questions":[],"answer":["minimal_patch"],"audit":"short"}'
        }
        content, structured_data = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("@flint v0 hybrid", content)
        self.assertIsNotNone(structured_data)

    def test_decode_variant_output_renders_debug_schema_payload(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-debug@schema-debug_hybrid=prompts/debug_hybrid_schema.txt")
        response = {
            "output_text": '{"mode":"hybrid","target":"auth_middleware","constraints":["backcompat","security"],"cause":"cmp(expiry,<,now)","patch":["add(grace30)"],"tests":["test(boundary_expiry)"],"risks":["auth_regression"],"answer":["minimal_patch"],"audit":"short"}'
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("G: fix(auth_middleware)", content)
        self.assertIn("H: cmp(expiry,<,now)", content)

    def test_decode_variant_output_renders_wire_payload(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-debug-wire@schema-debug_wire=prompts/debug_wire_schema.txt")
        response = {
            "output_text": '{"m":"hybrid","t":"auth_middleware","c":["backcompat","security"],"h":"cmp(expiry,<,now)","p":["add(grace30)"],"v":["test(boundary_expiry)"],"r":["auth_regression"],"a":["minimal_patch"]}'
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("@flint v0 hybrid", content)
        self.assertIn("G: fix(auth_middleware)", content)
        self.assertIn("[AUDIT]", content)
        self.assertIn("Fix auth middleware", content)

    def test_decode_variant_output_renders_wire_lite_payload(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-debug-wire-lite@schema-debug_wire_lite=prompts/debug_wire_lite.txt")
        response = {
            "output_text": '{"m":"hybrid","t":"auth_middleware","c":["backcompat","security"],"h":"cmp(expiry,<,now)","p":["add(grace30)"],"v":["test(boundary_expiry)"],"r":["auth_regression"],"a":["minimal_patch"]}'
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("@flint v0 hybrid", content)
        self.assertIn("G: fix(auth_middleware)", content)

    def test_decode_variant_output_expands_compact_audit_terms(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-debug-wire-lite@schema-debug_wire_lite=prompts/debug_wire_lite.txt")
        response = {
            "output_text": '{"m":"hybrid","t":"skew30","c":["bc","sec"],"h":"exp_lt_no_skew","p":["add(skew30)"],"v":["edge(-31s_401)"],"r":["timeunit_bug"],"a":["allow30s_skew"]}'
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("backward compatibility", content)
        self.assertIn("30-second grace window", content)
        self.assertIn("regression test", content)

    def test_decode_variant_output_canonicalizes_wire_lite_prose(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-review-wire-lite@schema-review_wire_lite=prompts/review_wire_lite.txt")
        response = {
            "output_text": '{"m":"hybrid","f":"header spoof issue","e":"attacker sets x-user-id","p":["strip header"],"v":["check 401"],"r":["unauthorized access"],"a":["use session only"]}'
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn('"header spoof issue"', content)
        self.assertIn('"attacker sets x-user-id"', content)

    def test_decode_variant_output_renders_architecture_wire_lite_payload(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-architecture-wire-lite@schema-architecture_wire_lite=prompts/architecture_wire_lite.txt")
        response = {
            "output_text": '{"m":"hybrid","d":"modular_monolith","c":["team(6)","timeline(\\"4 months\\")","store(\\"PostgreSQL\\")"],"h":["low_ops","fast_iteration"],"p":["ship_single_deployable"],"r":["modular_boundaries_decay"],"a":["default(modular_monolith)"]}'
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("G: decide(modular_monolith)", content)
        self.assertIn('timeline("4 months")', content)

    def test_decode_variant_output_canonicalizes_refactor_wire_lite_prose(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-refactor-wire-lite@schema-refactor_wire_lite=prompts/refactor_wire_lite.txt")
        response = {
            "output_text": '{"m":"hybrid","t":"loadUser","c":["same validation order","single next(err) path"],"p":["promisify db.findUser"],"v":["verify async await path"],"r":["behavior drift"],"a":["minimal async await migration"]}'
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("G: refactor(loadUser)", content)
        self.assertIn('"same validation order"', content)
        self.assertIn('"single next(err) path"', content)

    def test_decode_variant_output_renders_packed_payload(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-debug-pack@schema-debug_pack=prompts/debug_pack_schema.txt")
        response = {
            "output_text": '{"d":["hybrid","auth_middleware",["backcompat","security"],"cmp(expiry,<,now)",["add(grace30)"],["test(boundary_expiry)"],["auth_regression"],["minimal_patch"]]}'
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("@flint v0 hybrid", content)
        self.assertIn("G: fix(auth_middleware)", content)
        self.assertIn("[AUDIT]", content)

    def test_decode_variant_output_renders_slot_packed_payload(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-debug-slot-pack@schema-debug_slot_pack=prompts/debug_slot_pack_schema.txt")
        response = {
            "output_text": '{"d":["hybrid","auth_middleware","backcompat;security","cmp(expiry,<,now)","add(grace30)","test(boundary_expiry)","auth_regression","minimal_patch"]}'
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("@flint v0 hybrid", content)
        self.assertIn("C: backcompat ∧ security", content)
        self.assertIn("A: minimal_patch", content)

    def test_decode_variant_output_renders_draft2schema_payload(self) -> None:
        variant = RUN_OPENAI.parse_variant(
            "sigil-debug-d2s@draft2schema-debug_hybrid=prompts/hybrid_strict.txt::prompts/debug_hybrid_schema.txt"
        )
        response = {
            "output_text": '{"mode":"hybrid","target":"auth_middleware","constraints":["backcompat","security"],"cause":"cmp(expiry,<,now)","patch":["add(grace30)"],"tests":["test(boundary_expiry)"],"risks":["auth_regression"],"answer":["minimal_patch"],"audit":"short"}'
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("G: fix(auth_middleware)", content)
        self.assertIn("P: add(grace30)", content)

    def test_decode_variant_output_materializes_direct_sigil_audit(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-debug-direct@sigil=prompts/debug_direct_micro.txt")
        response = {
            "output_text": "@flint v0 hybrid\nG: fix(skew30)\nC: bc ∧ sec ∧ reg_t\nH: exp_lt_no_skew\nP: skew30 → edge(-30s_200)\nV: edge(-30s_200) ∧ edge(-31s_401)\nR: ! timeunit_bug\nA: allow30s_skew"
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("[AUDIT]", content)
        self.assertIn("backward compatibility", content)

    def test_decode_variant_output_repairs_direct_sigil_drift(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-debug-direct@sigil=prompts/debug_direct_sigil_micro.txt")
        response = {
            "output_text": "@flint v0 hybrid\nG: fix(auth_mw expiry skew30 boundary refresh_loop)\nC: expMs<nowMs−30000⇒401 ∧ expMs≥nowMs−30000⇒allow\nH: bc sec reg_t skew30 edge(-30s_200) edge(-31s_401)\nP: refresh_loop∧expMs≈nowMs−30000 → clamp_to_allow\nV: min_fix ∧ reg_test\nR: ! expMs<nowMs⇒401\nA: auth_mw"
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("[AUDIT]", content)
        self.assertIn("auth_mw_expiry_skew30_boundary_refresh_loop", content)
        self.assertIn("backward compatibility", content)

    def test_decode_variant_output_repairs_direct_sigil_header_drift(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-architecture-direct@sigil=prompts/architecture_direct_sigil_micro.txt")
        response = {
            "output_text": "@sigil_v0_hybrid\nG:decide(mod_monolith)\nC:team(6)∧ddl(\"4_months\")∧store(\"PostgreSQL\")∧traffic(modest)∧split(post_release)\nH:fast_ship∧low_ops⇒prefer(mod_monolith)\nP:monolith_now→shared_pg→slice_ready_modules\nR:!split_cost∧!premature_distrib\nA:mod_monolith"
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("@flint v0 hybrid", content)
        self.assertIn("[AUDIT]", content)
        self.assertIn("modular_monolith", content)
        self.assertIn('ddl("4 months")', content)

    def test_decode_variant_output_repairs_dangling_tail_operator(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-refactor-direct@sigil=prompts/refactor_direct_sigil_compact_v4.txt")
        response = {
            "output_text": "@flint v0 hybrid\nG: refactor(loadUser)\nC: same_order ∧ one_next(err)\nP: await(db.findUser) → await(audit.log)\nV: async_await ∧ minimal_async_await\nR: ! db_err->next(err) ∧"
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("[AUDIT]", content)
        self.assertIn("R: ! db_err->next(err)", content)
        self.assertIn("A: minimal_async_await", content)

    def test_decode_variant_output_injects_missing_header(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-debug-direct@sigil=prompts/debug_direct_sigil_compact_v4.txt")
        response = {
            "output_text": "G: fix(auth_mw)\nC: bc ∧ sec\nH: exp_lt_no_skew\nP: skew30_fix → keep_401\nV: reg_t ∧ edge(-31s_401)\nR: ! refresh_loop\nA: reg_t"
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertTrue(content.startswith("@flint v0 hybrid"))
        self.assertIn("[AUDIT]", content)

    def test_decode_variant_output_repairs_empty_tail_slot(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-architecture-direct@sigil=prompts/architecture_direct_sigil_claude_nano.txt")
        response = {
            "output_text": "@flint v0 hybrid\nG: mod_monolith\nC: team(8)∧ddl(\"6 weeks\")\nP: store(\"PostgreSQL\")∧shared_pg\nV:\nA:"
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("V: split(post_release)", content)
        self.assertIn("A: short_why", content)

    def test_decode_variant_output_repairs_bare_slot_tag(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-debug-direct@sigil=prompts/debug_direct_sigil_claude_nano.txt")
        response = {
            "output_text": "@flint v0 hybrid\nG: keep_401\nC: auth∧grace\nP: regression_test\nV\nA:"
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("V: edge(-30s_200)", content)
        self.assertIn("A: reg_t", content)

    def test_decode_variant_output_repairs_gemini_meta_header_drift(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-debug-gemini-nano@sigil=prompts/debug_direct_sigil_gemini_nano.txt")
        response = {
            "output_text": '[d] "<"\nG: "401"\nC: auth\nP: grace\nV: regression test\nA: keep_401 edge(-30s_200) edge(-31s_401)'
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertTrue(content.startswith("@flint v0 hybrid"))
        self.assertNotIn("[d]", content)
        self.assertIn("V: regression ∧ test", content)
        self.assertIn("A: keep_401 ∧ edge(-30s_200) ∧ edge(-31s_401)", content)
        parse_document(content)

    def test_decode_variant_output_repairs_header_at_end_and_stray_lines(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-refactor-gemini-nano@sigil=prompts/refactor_direct_sigil_gemini_nano.txt")
        response = {
            "output_text": " G: minimal\nC: same_order\nP: verify\nV: reconcileBatch\nA: async await next(err)\nAtoms: async, await, next(err), verify, minimal\nCalls: reconcileBatch, verify\n@flint v0 hybrid"
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertTrue(content.startswith("@flint v0 hybrid"))
        self.assertNotIn("Atoms:", content)
        self.assertNotIn("Calls:", content)
        self.assertIn("A: async ∧ await(next(err))", content)
        parse_document(content)

    def test_decode_variant_output_drops_stray_code_fence(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-debug-claude-nano@sigil=prompts/debug_direct_sigil_claude_nano.txt")
        response = {
            "output_text": "```\n@flint v0 hybrid\nG: auth_grace_regression_test\nC: keep_401 edge(-30s_200) edge(-31s_401)\nP: \"300\"|\"401"
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertNotIn("```", content)
        self.assertTrue(content.startswith("@flint v0 hybrid"))
        parse_document(content)

    def test_decode_variant_output_repairs_mixed_operator_fragments(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-review-gemini-nano@sigil=prompts/review_direct_sigil_gemini_nano.txt")
        response = {
            "output_text": 'G: review(patch)\nH: "returnTo"|"302" header spoof_denied\nP: drop_hdr keep_401\nV: auth risk verify\nA: keep_401'
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn('H: "returnTo"|"302" ∧ header ∧ spoof_denied', content)
        self.assertIn("P: drop_hdr ∧ keep_401", content)
        self.assertIn("V: auth ∧ risk ∧ verify", content)
        parse_document(content)

    def test_decode_variant_output_repairs_operator_runs_around_arrow(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-arch-openai-gemini-nano@sigil=prompts/architecture_direct_sigil_gemini_nano.txt")
        response = {
            "output_text": "C: team(small) + deadline(tight) + low_ops -> fast_ship priority"
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("C: team(small) ∧ deadline(tight) ∧ low_ops -> fast_ship ∧ priority", content)
        parse_document(content)

    def test_decode_variant_output_repairs_comparator_arrow_chain(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-debug-claude-nano@sigil=prompts/debug_direct_sigil_claude_nano.txt")
        response = {
            "output_text": "G: webhook_ts_reject∧valid_request∧edge_boundary\nC: abs(now-ts)>300→401∧clock_drift\nP: encode_grace"
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("gt(abs(now-ts),300) → 401", content)
        parse_document(content)

    def test_decode_variant_output_repairs_debug_delta_prose(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-debug-gemini-nano@sigil=prompts/debug_direct_sigil_gemini_nano.txt")
        response = {
            "output_text": "@flint v0 hybrid\nG: webhook_ts_validator rejects valid requests at abs(now-ts)==300\nC: rule_is_strict_gt_not_gte ∧ intended_budget_is_300s ∧ provider_skew_hits_boundary\nP: change abs(now-ts)>300 to abs(now-ts)>=301 OR abs(now-ts)>SKEW_BUDGET where SKEW_BUDGET=300\nV: edge(abs==300→200) ∧ edge(abs==301→401)\nA: keep_300s_budget ∧ fix_boundary_to_strict_gt"
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("eq(abs(now-ts),300)", content)
        self.assertIn("[AUDIT]", content)
        parse_document(content)

    def test_decode_variant_output_repairs_architecture_capsule_phrases(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-arch-openai-gemini-nano@sigil=prompts/architecture_direct_sigil_gemini_nano.txt")
        response = {
            "output_text": 'G: capsule micro architecture\nC: team 6; ddl 4 months; store PostgreSQL; ops pt_devops; traffic modest; split post_release\nA: short_why'
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn('C: team(6) ∧ ddl("4 months") ∧ store(PostgreSQL) ∧ ops(pt_devops) ∧ traffic(modest) ∧ split(post_release)', content)
        parse_document(content)

    def test_decode_variant_output_repairs_architecture_anchor_assignments(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-arch-openai-gemini-nano@sigil=prompts/architecture_direct_sigil_gemini_nano.txt")
        response = {
            "output_text": 'G: capsule micro architecture\nC: anchors="5"|"8 weeks"|"BigQuery"; team=5; ddl="8 weeks"; store="BigQuery"; ops=pt_dataops; traffic=batch_heavy; split=worker_later; deliver=default_arch short_why\nP:'
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn('anchor("5") ∧ anchor("8 weeks") ∧ anchor("BigQuery")', content)
        self.assertIn('store("BigQuery")', content)
        self.assertIn("deliver(default_arch_short_why)", content)
        self.assertIn("P: mod_monolith", content)
        parse_document(content)

    def test_decode_variant_output_repairs_architecture_why_tail(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-arch-openai-gemini-nano@sigil=prompts/architecture_direct_sigil_gemini_nano.txt")
        response = {
            "output_text": 'G: mod_monolith\nC: team(9)∧ddl("12 weeks")\nP: store("PostgreSQL")∧shared_pg\nV: compliance_ready∧platform_plus_sec\nA: split(post_release)∧mod_boundaries_now∧PostgreSQL_single_SoR∧why: 9-person team + 12-week window makes distributed-systems overhead net-negative'
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("why(9_person_team_12_week_window_makes_distributed)", content)
        parse_document(content)

    def test_decode_variant_output_repairs_architecture_broken_pipe_plan(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-arch-openai-gemini-nano@sigil=prompts/architecture_direct_sigil_gemini_nano.txt")
        response = {
            "output_text": 'G: capsule micro architecture\nC: team 6; ddl 4 months; store PostgreSQL; ops pt_devops\nP: 6 | 4 months | PostgreSQL | team 6 | ddl 4 months |'
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("P: mod_monolith", content)
        parse_document(content)

    def test_decode_variant_output_drops_unknown_slot_tag(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-debug-gemini-nano@sigil=prompts/debug_direct_sigil_gemini_nano.txt")
        response = {
            "output_text": 'G: auth grace regression test keep_401\nC: "1000"|"401"\nP: edge(-30s_200)\nV: edge(-31s_401)\nA: keep_401\nS: auth grace regression test keep_401 edge(-30s_200) edge(-31s_401)'
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertNotIn("\nS:", content)
        self.assertIn("A: keep_401", content)
        parse_document(content)

    def test_decode_variant_output_repairs_refactor_gemini_pseudocode_chain(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-refactor-gemini-nano@sigil=prompts/refactor_direct_sigil_gemini_nano.txt")
        response = {
            "output_text": "@flint v0 hybrid\nG: sendEmailReceipt async await verify minimal same_order next(err)\nC: async sendEmailReceipt(order) { await verify(order); next(err); }\nP: sendEmailReceipt(order).then(verify)."
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("C: async ∧ sendEmailReceipt(order) ∧ await(verify(order)) ∧ next(err)", content)
        self.assertIn("P: sendEmailReceipt(order) ∧ then(verify)", content)
        parse_document(content)

    def test_decode_variant_output_repairs_refactor_signature_drift(self) -> None:
        variant = RUN_OPENAI.parse_variant("sigil-refactor-gemini-nano@sigil=prompts/refactor_direct_sigil_gemini_nano.txt")
        response = {
            "output_text": "@flint v0 hybrid\nG: loadGatewayUser :: async (req, res, next) -> session_check → db.findUser → flags.load → audit.log → next\nC: session_check | db.\nA:"
        }
        content, _ = RUN_OPENAI.decode_variant_output(variant, response)
        self.assertIn("[AUDIT]", content)
        self.assertIn("G: loadGatewayUser ∧ async ∧ session_check ∧ db.findUser ∧ flags.load ∧ audit.log ∧ next", content)
        parse_document(content)

    def test_merge_usage_sums_stage_totals(self) -> None:
        merged = RUN_OPENAI.merge_usage(
            [
                {"input_tokens": 10, "output_tokens": 3, "total_tokens": 13, "cached_tokens": 2, "reasoning_tokens": 0},
                {"input_tokens": 20, "output_tokens": 7, "total_tokens": 27, "cached_tokens": 5, "reasoning_tokens": 1},
            ]
        )
        self.assertEqual(merged["stage_count"], 2)
        self.assertEqual(merged["input_tokens"], 30)
        self.assertEqual(merged["output_tokens"], 10)
        self.assertEqual(merged["total_tokens"], 40)
        self.assertEqual(merged["cached_tokens"], 7)
        self.assertEqual(merged["reasoning_tokens"], 1)

    def test_build_conditioned_task_prompt_embeds_draft(self) -> None:
        prompt = RUN_OPENAI.build_conditioned_task_prompt("Original task.", "@flint v0 hybrid\nG: fix(auth)")
        self.assertIn("Original task.", prompt)
        self.assertIn("<draft>", prompt)
        self.assertIn("G: fix(auth)", prompt)

    def test_strip_wrapping_code_fences(self) -> None:
        fenced = "```plaintext\n@flint v0 hybrid\nG: fix(auth)\n```"
        self.assertEqual(RUN_OPENAI.strip_wrapping_code_fences(fenced), "@flint v0 hybrid\nG: fix(auth)")


if __name__ == "__main__":
    unittest.main()
