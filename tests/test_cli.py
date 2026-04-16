from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from sigil.cli import main


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_validate_command(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(["validate", str(ROOT / "examples" / "debugging.sigil")])
        self.assertEqual(exit_code, 0)
        self.assertIn("OK:", buffer.getvalue())

    def test_audit_command(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(["audit", str(ROOT / "examples" / "architecture.sigil")])
        self.assertEqual(exit_code, 0)
        self.assertIn("Default recommendation", buffer.getvalue())

    def test_stats_command(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(["stats", str(ROOT / "examples" / "debugging.sigil"), "--json"])
        self.assertEqual(exit_code, 0)
        self.assertIn('"clause_count": 8', buffer.getvalue())

    def test_repair_command(self) -> None:
        path = ROOT / "tests" / "fixtures_repair_input.sigil"
        path.write_text("@sigil v0 hybrid\nP: try(await db_findUser) → next(err)\n[AUDIT]\nshort\n", encoding="utf-8")
        buffer = io.StringIO()
        try:
            with redirect_stdout(buffer):
                exit_code = main(["repair", str(path)])
            self.assertEqual(exit_code, 0)
            self.assertIn("await(db_findUser)", buffer.getvalue())
        finally:
            path.unlink(missing_ok=True)

    def test_bench_build_corpus_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(["bench", "build-corpus", "--out-dir", tmpdir])
            self.assertEqual(exit_code, 0)
            summary = json.loads(buffer.getvalue())
            self.assertIn("hybrid", summary["outputs"])
            self.assertTrue((Path(tmpdir) / "tasks_hybrid_micro_extended.jsonl").exists())

    def test_bench_build_macro_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "tasks.jsonl"
            prefix = root / "prefix.txt"
            out = root / "macro.jsonl"
            source.write_text(
                json.dumps({"id": "t1", "prompt": "Fix the bug.", "category": "debugging", "mode": "hybrid"}) + "\n",
                encoding="utf-8",
            )
            prefix.write_text("Stable context.", encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(["bench", "build-macro", str(source), str(prefix), str(out)])
            self.assertEqual(exit_code, 0)
            summary = json.loads(buffer.getvalue())
            self.assertEqual(summary["count"], 1)
            self.assertTrue(out.exists())

    def test_bench_build_compiled_macro_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "tasks.jsonl"
            prefix = ROOT / "evals" / "prefixes" / "service_context_v1.txt"
            out = root / "macro_compiled.jsonl"
            source.write_text(
                json.dumps({"id": "t1", "prompt": "Fix the bug.", "category": "debugging", "mode": "hybrid"}) + "\n",
                encoding="utf-8",
            )
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(
                    [
                        "bench",
                        "build-compiled-macro",
                        str(source),
                        str(prefix),
                        str(out),
                        "--context-style",
                        "focused",
                    ]
                )
            self.assertEqual(exit_code, 0)
            summary = json.loads(buffer.getvalue())
            self.assertEqual(summary["count"], 1)
            row = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row["benchmark_scale"], "macro-focused")
            self.assertEqual(row["context_style"], "focused")

    def test_bench_build_compiled_macro_targeted_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "tasks.jsonl"
            prefix = ROOT / "evals" / "prefixes" / "service_context_v1.txt"
            out = root / "macro_targeted.jsonl"
            source.write_text(
                json.dumps(
                    {
                        "id": "t1",
                        "prompt": "Fix auth expiry around x-user-id and 401.",
                        "category": "debugging",
                        "mode": "hybrid",
                        "exact_literals": ["x-user-id", "401"],
                        "must_include": ["expiry", "boundary"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(
                    [
                        "bench",
                        "build-compiled-macro",
                        str(source),
                        str(prefix),
                        str(out),
                        "--context-style",
                        "targeted",
                    ]
                )
            self.assertEqual(exit_code, 0)
            row = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row["benchmark_scale"], "macro-targeted")
            self.assertEqual(row["context_style"], "targeted")
            self.assertIn('anchors: "x-user-id" | "401"', row["cache_prefix"])

    def test_bench_build_capsules_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = ROOT / "evals" / "tasks_review.jsonl"
            out = root / "tasks_review_nano.jsonl"
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(["bench", "build-capsules", str(source), str(out), "--style", "nano"])
            self.assertEqual(exit_code, 0)
            summary = json.loads(buffer.getvalue())
            self.assertEqual(summary["count"], 1)
            row = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row["capsule"], "nano")

    def test_bench_report_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tasks = root / "tasks.jsonl"
            run = root / "run.jsonl"
            manifest = root / "manifest.json"
            out = root / "results.md"
            tasks.write_text(
                json.dumps(
                    {
                        "id": "t1",
                        "category": "debugging",
                        "mode": "hybrid",
                        "prompt": "Fix auth expiry.",
                        "must_include": ["auth"],
                        "exact_literals": ["401"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            sigil_text = (
                "@sigil v0 hybrid\n"
                "G: fix(auth)\n"
                "P: keep_401\n"
                "A: auth\n\n"
                "[AUDIT]\n"
                "Goal: fix(auth).\n"
                "Plan: keep 401.\n"
                "Answer target: auth 401.\n"
            )
            run.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "task_id": "t1",
                                "variant": "baseline-terse",
                                "model": "demo-model",
                                "transport": "plain",
                                "structured_expected": False,
                                "content": "Fix auth and keep 401.",
                                "usage": {"input_tokens": 20, "output_tokens": 12, "total_tokens": 32, "cached_tokens": 0},
                                "elapsed_ms": 20,
                            }
                        ),
                        json.dumps(
                            {
                                "task_id": "t1",
                                "variant": "sigil-routed",
                                "model": "demo-model",
                                "provider": "openai",
                                "transport": "sigil",
                                "structured_expected": True,
                                "content": sigil_text,
                                "usage": {"input_tokens": 18, "output_tokens": 8, "total_tokens": 26, "cached_tokens": 0},
                                "elapsed_ms": 10,
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            manifest.write_text(
                json.dumps(
                    {
                        "title": "Demo Report",
                        "entries": [
                            {
                                "label": "Demo",
                                "provider": "openai",
                                "model": "gpt-5.4-mini",
                                "regime": "micro",
                                "router": "selective",
                                "tasks": str(tasks),
                                "run": str(run),
                                "baseline": "baseline-terse",
                                "variant": "sigil-routed",
                                "primary_metric": "total",
                                "notes": "Demo note."
                            }
                        ],
                        "corpora": [{"label": "Demo corpus", "path": str(tasks)}],
                    }
                ),
                encoding="utf-8",
            )
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(["bench", "report", str(manifest), "--out", str(out)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(out.exists())
            report = out.read_text(encoding="utf-8")
            self.assertIn("Demo Report", report)
            self.assertIn("gpt-5.4-mini", report)
            self.assertIn("18.75%", report)

    def test_bench_portability_report_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tasks = root / "tasks.jsonl"
            run = root / "run.jsonl"
            out = root / "portability.md"
            tasks.write_text(
                json.dumps(
                    {
                        "id": "t1",
                        "category": "code_review",
                        "mode": "hybrid",
                        "prompt": "Review auth header spoof.",
                        "must_include": ["auth"],
                        "exact_literals": ["401"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            sigil_text = (
                "@sigil v0 hybrid\n"
                "G: auth_review\n"
                "P: keep_401\n"
                "A: sess_only\n\n"
                "[AUDIT]\n"
                "Goal: auth review.\n"
                "Plan: keep 401.\n"
                "Answer target: session only.\n"
            )
            run.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "task_id": "t1",
                                "variant": "baseline-terse",
                                "model": "demo-model",
                                "provider": "openai",
                                "transport": "plain",
                                "prompt_path": "prompts/baseline_terse.txt",
                                "structured_expected": False,
                                "content": "Review auth and keep 401.",
                                "usage": {"input_tokens": 20, "output_tokens": 12, "total_tokens": 32, "cached_tokens": 0},
                                "elapsed_ms": 20,
                            }
                        ),
                        json.dumps(
                            {
                                "task_id": "t1",
                                "variant": "sigil-review-gemini-transfer",
                                "model": "demo-model",
                                "provider": "openai",
                                "transport": "sigil",
                                "prompt_path": "prompts/review_direct_sigil_gemini_nano.txt",
                                "structured_expected": True,
                                "content": sigil_text,
                                "usage": {"input_tokens": 18, "output_tokens": 8, "total_tokens": 26, "cached_tokens": 0},
                                "elapsed_ms": 10,
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(["bench", "portability-report", str(tasks), str(run), "--out", str(out)])
            self.assertEqual(exit_code, 0)
            report = out.read_text(encoding="utf-8")
            self.assertIn("SIGIL Contract Portability", report)
            self.assertIn("gemini-nano", report)
            self.assertIn("openai", report)


if __name__ == "__main__":
    unittest.main()
