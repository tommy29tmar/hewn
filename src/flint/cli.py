from __future__ import annotations

import argparse
import json
from pathlib import Path

from .bench import (
    build_adaptive_run,
    build_compiled_macro_tasks,
    build_extended_corpus,
    build_macro_tasks,
    build_task_capsules,
    render_portability_report,
    render_report,
)
from .metrics import document_metrics
from .normalize import normalize_document_text, repair_direct_flint_text
from .parser import FlintParseError, document_to_data, parse_document
from .render import generate_audit


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sigil", description="Parse and validate SIGIL documents.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a .sigil file.")
    validate_parser.add_argument("path", type=Path)

    parse_parser = subparsers.add_parser("parse", help="Parse a .sigil file.")
    parse_parser.add_argument("path", type=Path)
    parse_parser.add_argument("--json", action="store_true", help="Print parsed output as JSON.")

    audit_parser = subparsers.add_parser("audit", help="Render the audit view for a .sigil file.")
    audit_parser.add_argument("path", type=Path)
    audit_parser.add_argument(
        "--explain",
        action="store_true",
        help="Show raw / repaired / parse-state / anchor checks / prose audit side by side.",
    )
    audit_parser.add_argument(
        "--anchor",
        dest="anchors",
        action="append",
        default=None,
        help="Anchor to check (repeat to pass multiple); reports hit/missed against the raw text.",
    )
    audit_parser.add_argument(
        "--category",
        default="",
        help="Hint for the repair layer (debugging / architecture / code_review / refactoring).",
    )

    stats_parser = subparsers.add_parser("stats", help="Show structural and size metrics for a .sigil file.")
    stats_parser.add_argument("path", type=Path)
    stats_parser.add_argument("--json", action="store_true", help="Print metrics as JSON.")

    repair_parser = subparsers.add_parser("repair", help="Apply deterministic normalization to a .sigil-like file.")
    repair_parser.add_argument("path", type=Path)

    bench_parser = subparsers.add_parser("bench", help="Benchmark helpers for corpus generation and reporting.")
    bench_subparsers = bench_parser.add_subparsers(dest="bench_command", required=True)

    bench_corpus_parser = bench_subparsers.add_parser("build-corpus", help="Build the extended micro corpus.")
    bench_corpus_parser.add_argument("--out-dir", type=Path, default=Path("evals"))

    bench_macro_parser = bench_subparsers.add_parser("build-macro", help="Build macro tasks with a shared cache prefix.")
    bench_macro_parser.add_argument("source", type=Path)
    bench_macro_parser.add_argument("prefix", type=Path)
    bench_macro_parser.add_argument("out", type=Path)
    bench_macro_parser.add_argument("--task-label", default="Task")

    bench_compiled_macro_parser = bench_subparsers.add_parser(
        "build-compiled-macro",
        help="Build macro tasks with a compiled shared context prefix.",
    )
    bench_compiled_macro_parser.add_argument("source", type=Path)
    bench_compiled_macro_parser.add_argument("prefix", type=Path)
    bench_compiled_macro_parser.add_argument("out", type=Path)
    bench_compiled_macro_parser.add_argument(
        "--context-style",
        choices=["cacheable", "focused", "targeted", "needle", "delta", "layered", "layered-needle", "layered-delta"],
        default="cacheable",
    )
    bench_compiled_macro_parser.add_argument("--task-label", default="Task")

    bench_capsule_parser = bench_subparsers.add_parser("build-capsules", help="Build local task capsules from a task file.")
    bench_capsule_parser.add_argument("source", type=Path)
    bench_capsule_parser.add_argument("out", type=Path)
    bench_capsule_parser.add_argument("--style", choices=["v1", "micro", "nano", "bridge"], default="v1")

    bench_adaptive_parser = bench_subparsers.add_parser(
        "build-adaptive-run",
        help="Build a verifier-gated adaptive run with fallback expansion.",
    )
    bench_adaptive_parser.add_argument("tasks", type=Path)
    bench_adaptive_parser.add_argument("out", type=Path)
    bench_adaptive_parser.add_argument("--candidate-run", dest="candidate_runs", action="append", type=Path, default=None)
    bench_adaptive_parser.add_argument("--primary-run", dest="primary_runs", action="append", type=Path, default=None)
    bench_adaptive_parser.add_argument("--fallback-run", dest="fallback_runs", action="append", type=Path, default=None)
    bench_adaptive_parser.add_argument("--baseline-run", type=Path, default=None)
    bench_adaptive_parser.add_argument("--baseline-variant", default="baseline-terse")
    bench_adaptive_parser.add_argument("--variant-name", default="sigil-adaptive")
    bench_adaptive_parser.add_argument("--min-must-include", type=float, default=0.75)
    bench_adaptive_parser.add_argument("--min-exact-literal", type=float, default=0.75)
    bench_adaptive_parser.add_argument("--allow-repair", action="store_true")
    bench_adaptive_parser.add_argument("--no-require-parse", action="store_true")
    bench_adaptive_parser.add_argument("--no-require-mode-match", action="store_true")

    bench_report_parser = bench_subparsers.add_parser("report", help="Render a Markdown benchmark report from a manifest.")
    bench_report_parser.add_argument("manifest", type=Path)
    bench_report_parser.add_argument("--out", type=Path, default=None)

    bench_portability_parser = bench_subparsers.add_parser(
        "portability-report",
        help="Render a Markdown report of contract-family portability across run files.",
    )
    bench_portability_parser.add_argument("tasks", type=Path)
    bench_portability_parser.add_argument("runs", type=Path, nargs="+")
    bench_portability_parser.add_argument("--out", type=Path, default=None)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "repair":
        raw_text = args.path.read_text(encoding="utf-8")
        print(normalize_document_text(raw_text))
        return 0

    if args.command == "bench":
        if args.bench_command == "build-corpus":
            result = build_extended_corpus(args.out_dir)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        if args.bench_command == "build-macro":
            result = build_macro_tasks(args.source, args.prefix, args.out, task_label=args.task_label)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        if args.bench_command == "build-compiled-macro":
            result = build_compiled_macro_tasks(
                args.source,
                args.prefix,
                args.out,
                context_style=args.context_style,
                task_label=args.task_label,
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        if args.bench_command == "build-capsules":
            result = build_task_capsules(args.source, args.out, style=args.style)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        if args.bench_command == "build-adaptive-run":
            result = build_adaptive_run(
                args.tasks,
                args.out,
                candidate_runs=args.candidate_runs,
                primary_runs=args.primary_runs,
                fallback_runs=args.fallback_runs,
                baseline_run=args.baseline_run,
                baseline_variant=args.baseline_variant,
                variant_name=args.variant_name,
                min_must_include=args.min_must_include,
                min_exact_literal=args.min_exact_literal,
                allow_repair=args.allow_repair,
                require_parse=not args.no_require_parse,
                require_mode_match=not args.no_require_mode_match,
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        if args.bench_command == "report":
            markdown = render_report(args.manifest, args.out)
            if args.out is None:
                print(markdown, end="")
            else:
                print(f"Wrote {args.out}")
            return 0
        if args.bench_command == "portability-report":
            markdown = render_portability_report(args.tasks, args.runs, args.out)
            if args.out is None:
                print(markdown, end="")
            else:
                print(f"Wrote {args.out}")
            return 0
        parser.exit(status=2, message="sigil: unknown bench command\n")
        return 2

    if args.command == "audit" and getattr(args, "explain", False):
        return _run_audit_explain(args.path, getattr(args, "anchors", None) or [], getattr(args, "category", "") or "")

    try:
        document = parse_document(args.path)
    except FlintParseError as exc:
        parser.exit(status=1, message=f"sigil: {exc}\n")

    if args.command == "validate":
        mode = document.header.mode if document.header else "unspecified"
        print(f"OK: {args.path} (mode={mode}, clauses={len(document.clauses)}, codebook={len(document.codebook)})")
        return 0

    if args.command == "parse":
        if args.json:
            print(json.dumps(document_to_data(document), indent=2, ensure_ascii=False))
        else:
            print(document)
        return 0

    if args.command == "audit":
        print(generate_audit(document))
        return 0

    if args.command == "stats":
        raw_text = args.path.read_text(encoding="utf-8")
        stats = document_metrics(document, raw_text)
        if args.json:
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(stats, ensure_ascii=False))
        return 0

    parser.exit(status=2, message="sigil: unknown command\n")
    return 2


def _run_audit_explain(path: Path, anchors: list[str], category: str) -> int:
    raw = path.read_text(encoding="utf-8")
    repaired = repair_direct_flint_text(raw, category)
    parse_state: str
    prose: str
    try:
        document = parse_document(repaired)
        parse_state = "OK"
        prose = generate_audit(document)
    except FlintParseError as exc:
        parse_state = f"FAIL: {exc}"
        prose = "(unparseable — showing repaired SIGIL only)"

    def _panel(title: str, body: str) -> None:
        print(f"=== {title} ===")
        print(body.rstrip())
        print()

    _panel(f"RAW ({len(raw)} chars)", raw)
    if repaired.strip() != raw.strip():
        _panel("REPAIRED", repaired)
    _panel("PARSE", parse_state)
    if anchors:
        hit = [a for a in anchors if a in raw]
        missed = [a for a in anchors if a not in raw]
        _panel(
            "ANCHORS",
            f"hit:    {hit if hit else '(none)'}\nmissed: {missed if missed else '(none)'}",
        )
    _panel("PROSE AUDIT", prose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
