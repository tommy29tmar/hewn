from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .metrics import document_metrics
from .normalize import normalize_document_text, repair_direct_flint_text
from .parser import FlintParseError, document_to_data, parse_document
from .render import generate_audit
from .claude_code import cached_compile, compile_claude_md
from .routing import load_profile, pick_variant


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flint-ir", description="Parse and validate Flint documents.")
    parser.add_argument("--version", action="version", version=f"flint-ir {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a .flint file.")
    validate_parser.add_argument("path", type=Path)

    parse_parser = subparsers.add_parser("parse", help="Parse a .flint file.")
    parse_parser.add_argument("path", type=Path)
    parse_parser.add_argument("--json", action="store_true", help="Print parsed output as JSON.")

    audit_parser = subparsers.add_parser("audit", help="Render the audit view for a .flint file.")
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

    stats_parser = subparsers.add_parser("stats", help="Show structural and size metrics for a .flint file.")
    stats_parser.add_argument("path", type=Path)
    stats_parser.add_argument("--json", action="store_true", help="Print metrics as JSON.")

    repair_parser = subparsers.add_parser("repair", help="Apply deterministic normalization to a .flint-like file.")
    repair_parser.add_argument("path", type=Path)

    claude_code_parser = subparsers.add_parser(
        "claude-code",
        help="Per-file CLAUDE.md audit tools (compile / diff / inventory).",
    )
    claude_code_sub = claude_code_parser.add_subparsers(dest="claude_code_command", required=True)

    cc_compile = claude_code_sub.add_parser("compile", help="Print the structurally-safe compressed form of the file.")
    cc_compile.add_argument("path", type=Path)
    cc_compile.add_argument("--no-cache", action="store_true")

    cc_diff = claude_code_sub.add_parser("diff", help="Unified diff of original vs compressed with segment annotations.")
    cc_diff.add_argument("path", type=Path)
    cc_diff.add_argument("--no-cache", action="store_true")

    cc_inventory = claude_code_sub.add_parser(
        "inventory",
        help="For each given file, print original vs compressed token counts.",
    )
    cc_inventory.add_argument("paths", type=Path, nargs="+")
    cc_inventory.add_argument("--no-cache", action="store_true")

    routing_parser = subparsers.add_parser("routing", help="Inspect existing routing profiles.")
    routing_subparsers = routing_parser.add_subparsers(dest="routing_command", required=True)

    routing_recommend = routing_subparsers.add_parser(
        "recommend",
        help="Print the variant recommended by a profile for a task or category.",
    )
    routing_recommend.add_argument("--profile", type=Path, required=True, help="Path to the profile JSON.")
    routing_recommend.add_argument("--task-id", default=None, help="Look up task-specific override first.")
    routing_recommend.add_argument("--category", default=None, help="Fall back to category mapping.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "repair":
        raw_text = args.path.read_text(encoding="utf-8")
        print(normalize_document_text(raw_text))
        return 0

    if args.command == "claude-code":
        return _run_claude_code(args, parser)

    if args.command == "routing":
        if args.routing_command == "recommend":
            try:
                profile = load_profile(args.profile)
            except (ValueError, OSError) as exc:
                parser.exit(status=1, message=f"flint-ir: {exc}\n")
            pick = pick_variant(profile, task_id=args.task_id, category=args.category)
            if pick is None:
                print("(none)")
                return 1
            print(pick)
            return 0
        parser.exit(status=2, message="flint-ir: unknown routing command\n")
        return 2

    if args.command == "audit" and getattr(args, "explain", False):
        return _run_audit_explain(args.path, getattr(args, "anchors", None) or [], getattr(args, "category", "") or "")

    try:
        document = parse_document(args.path)
    except FlintParseError as exc:
        parser.exit(status=1, message=f"flint-ir: {exc}\n")

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

    parser.exit(status=2, message="flint-ir: unknown command\n")
    return 2


def _run_claude_code(args, parser) -> int:
    import difflib

    def _compile(path: Path):
        if getattr(args, "no_cache", False):
            return compile_claude_md(path)
        return cached_compile(path)

    if args.claude_code_command == "compile":
        if not args.path.exists():
            parser.exit(status=1, message=f"flint-ir: file not found: {args.path}\n")
        ctx = _compile(args.path)
        sys.stdout.write(ctx.compressed_text)
        if not ctx.compressed_text.endswith("\n"):
            sys.stdout.write("\n")
        return 0
    if args.claude_code_command == "diff":
        if not args.path.exists():
            parser.exit(status=1, message=f"flint-ir: file not found: {args.path}\n")
        ctx = _compile(args.path)
        diff = difflib.unified_diff(
            ctx.original_text.splitlines(keepends=True),
            ctx.compressed_text.splitlines(keepends=True),
            fromfile=f"{args.path} (original, ~{ctx.original_tokens} tok)",
            tofile=f"{args.path} (compressed, ~{ctx.compressed_tokens} tok)",
        )
        sys.stdout.write("".join(diff))
        preserved = sum(1 for s in ctx.segments if s.preserved_verbatim)
        compressed_count = sum(1 for s in ctx.segments if not s.preserved_verbatim)
        print(f"\n# summary: {preserved} segment(s) verbatim, {compressed_count} compressed")
        return 0
    if args.claude_code_command == "inventory":
        total_orig = 0
        total_comp = 0
        print(f"{'file':<60} {'orig_tok':>9} {'comp_tok':>9} {'delta':>7}")
        for path in args.paths:
            if not path.exists():
                print(f"{str(path):<60} MISSING")
                continue
            ctx = _compile(path)
            delta = ctx.compressed_tokens - ctx.original_tokens
            total_orig += ctx.original_tokens
            total_comp += ctx.compressed_tokens
            print(f"{str(path):<60} {ctx.original_tokens:>9} {ctx.compressed_tokens:>9} {delta:>+7}")
        if len(args.paths) > 1:
            print(f"{'TOTAL':<60} {total_orig:>9} {total_comp:>9} {total_comp - total_orig:>+7}")
        return 0
    parser.exit(status=2, message="flint-ir: unknown claude-code command\n")
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
        prose = "(unparseable — showing repaired Flint only)"

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
