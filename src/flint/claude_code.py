"""Per-file CLAUDE.md compile/diff audit.

Read-only helpers that compress whitespace in plain prose bullets while
preserving code, commands, paths, headings, and anything ambiguous. This
module does NOT walk the filesystem and does NOT mirror Claude Code's own
memory resolution rules. It answers: 'given THIS file, what would a
structurally-safe compressed version look like?'

Design:
- Parse the file into segments by kind (heading, fenced_code,
  command_or_path, inline_code_paragraph, list_item_prose, other).
- Only 'list_item_prose' is eligible for compression.
- Compression is whitespace-only via safe_collapse_prose: collapses runs
  of whitespace and strips leading/trailing, but refuses to change any
  non-whitespace character.
- Everything else is preserved byte-for-byte.
- Cached by sha1 of the original text under ~/.cache/flint/claude-code/
  (or $FLINT_CACHE_DIR/claude-code/).
"""
from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .metrics import approx_token_count

FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^\s*#{1,6}\s")
LIST_ITEM_RE = re.compile(r"^(\s*)([-*+]\s|\d+[.)]\s)(.*)$")
COMMAND_RE = re.compile(r"^\s*(\$|>|#!)")
PATH_HINT_RE = re.compile(
    r"(^|\s)(?:/[\w./-]+|\./[\w./-]+|~/[\w./-]+|\w+/[\w./-]+\.\w+)"
)


@dataclass
class Segment:
    kind: str
    original_text: str
    compressed_text: str
    preserved_verbatim: bool
    reason: str = ""


@dataclass
class CompiledContext:
    original_text: str
    compressed_text: str
    original_tokens: int
    compressed_tokens: int
    segments: list[Segment] = field(default_factory=list)
    hash: str = ""


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def safe_collapse_prose(text: str) -> str:
    """Whitespace-only normalize. Refuses to change any non-whitespace char.

    If collapsing would change anything other than whitespace, the original
    text is returned unchanged.
    """
    collapsed = re.sub(r"[ \t]+", " ", text.strip())
    # Check invariant: stripping whitespace differences, both strings must be identical.
    def _ws_normal(s: str) -> str:
        return re.sub(r"\s+", " ", s).strip()

    if _ws_normal(text) != _ws_normal(collapsed):
        return text
    # Collapsed text may only differ from original in whitespace — verify no
    # non-whitespace character changed position/identity.
    if _strip_ws(text) != _strip_ws(collapsed):
        return text
    return collapsed


def _strip_ws(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _is_fenced_open(line: str) -> bool:
    return bool(FENCE_RE.match(line))


def _line_looks_like_command_or_path(line: str) -> bool:
    if COMMAND_RE.match(line):
        return True
    stripped = line.strip()
    if stripped.startswith(("/", "./", "~/")):
        return True
    if PATH_HINT_RE.search(line) and not HEADING_RE.match(line):
        return True
    return False


def _paragraph_has_inline_code(paragraph_text: str) -> bool:
    # A paragraph has inline code if it contains backticks that form a valid
    # inline-code span (simplification: any backtick).
    return "`" in paragraph_text


def segment_markdown(text: str) -> list[Segment]:
    """Parse markdown into typed segments. Lossless: concatenating every
    segment's original_text reproduces the input byte-for-byte."""
    segments: list[Segment] = []
    lines = text.splitlines(keepends=True)
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        raw_line = line.rstrip("\n\r")
        # Fenced code block: capture until matching fence or EOF.
        fence_match = FENCE_RE.match(raw_line)
        if fence_match:
            fence_marker = fence_match.group(1)
            block_lines = [line]
            i += 1
            while i < n:
                block_lines.append(lines[i])
                closing = lines[i].rstrip("\n\r")
                if closing.strip().startswith(fence_marker):
                    i += 1
                    break
                i += 1
            block_text = "".join(block_lines)
            segments.append(Segment(
                kind="fenced_code",
                original_text=block_text,
                compressed_text=block_text,
                preserved_verbatim=True,
                reason="fenced code block",
            ))
            continue
        # Heading.
        if HEADING_RE.match(raw_line):
            segments.append(Segment(
                kind="heading",
                original_text=line,
                compressed_text=line,
                preserved_verbatim=True,
                reason="markdown heading",
            ))
            i += 1
            continue
        # Command or path-like line.
        if raw_line.strip() and _line_looks_like_command_or_path(raw_line):
            segments.append(Segment(
                kind="command_or_path",
                original_text=line,
                compressed_text=line,
                preserved_verbatim=True,
                reason="command or path",
            ))
            i += 1
            continue
        # List item.
        list_match = LIST_ITEM_RE.match(raw_line)
        if list_match:
            body = list_match.group(3) or ""
            if _paragraph_has_inline_code(body):
                segments.append(Segment(
                    kind="inline_code_paragraph",
                    original_text=line,
                    compressed_text=line,
                    preserved_verbatim=True,
                    reason="inline code in list item",
                ))
                i += 1
                continue
            if _line_looks_like_command_or_path(body):
                segments.append(Segment(
                    kind="command_or_path",
                    original_text=line,
                    compressed_text=line,
                    preserved_verbatim=True,
                    reason="path-like content in list item",
                ))
                i += 1
                continue
            # Eligible for whitespace-only compression; keep the bullet prefix.
            indent = list_match.group(1) or ""
            marker = list_match.group(2) or ""
            collapsed_body = safe_collapse_prose(body)
            compressed = f"{indent}{marker}{collapsed_body}\n" if line.endswith("\n") else f"{indent}{marker}{collapsed_body}"
            preserved = compressed == line
            segments.append(Segment(
                kind="list_item_prose",
                original_text=line,
                compressed_text=compressed,
                preserved_verbatim=preserved,
                reason="prose list item" if not preserved else "no whitespace to collapse",
            ))
            i += 1
            continue
        # Blank line — preserve as its own segment so concatenation is lossless.
        if not raw_line.strip():
            segments.append(Segment(
                kind="other",
                original_text=line,
                compressed_text=line,
                preserved_verbatim=True,
                reason="blank line",
            ))
            i += 1
            continue
        # Paragraph line — if it has inline code, preserve; otherwise it is
        # free prose which we DO NOT compress (safer: only explicit list items
        # are eligible, to avoid touching unknown structure).
        if _paragraph_has_inline_code(raw_line):
            segments.append(Segment(
                kind="inline_code_paragraph",
                original_text=line,
                compressed_text=line,
                preserved_verbatim=True,
                reason="paragraph with inline code",
            ))
        else:
            segments.append(Segment(
                kind="other",
                original_text=line,
                compressed_text=line,
                preserved_verbatim=True,
                reason="paragraph prose",
            ))
        i += 1
    return segments


def compile_claude_md(path: Path) -> CompiledContext:
    """Compile a single CLAUDE.md (or any markdown file)."""
    original = path.read_text(encoding="utf-8")
    segments = segment_markdown(original)
    compressed = "".join(s.compressed_text for s in segments)
    return CompiledContext(
        original_text=original,
        compressed_text=compressed,
        original_tokens=approx_token_count(original),
        compressed_tokens=approx_token_count(compressed),
        segments=segments,
        hash=_sha1(original),
    )


def cache_dir() -> Path:
    base = os.environ.get("FLINT_CACHE_DIR")
    if base:
        return Path(base).expanduser() / "claude-code"
    return Path.home() / ".cache" / "flint" / "claude-code"


def cached_compile(path: Path) -> CompiledContext:
    """Compile with sha1-keyed caching under cache_dir()."""
    original = path.read_text(encoding="utf-8")
    digest = _sha1(original)
    cdir = cache_dir()
    cdir.mkdir(parents=True, exist_ok=True)
    cache_file = cdir / f"{digest}.md"
    if cache_file.exists():
        compressed = cache_file.read_text(encoding="utf-8")
        segments = segment_markdown(original)
        return CompiledContext(
            original_text=original,
            compressed_text=compressed,
            original_tokens=approx_token_count(original),
            compressed_tokens=approx_token_count(compressed),
            segments=segments,
            hash=digest,
        )
    ctx = compile_claude_md(path)
    cache_file.write_text(ctx.compressed_text, encoding="utf-8")
    return ctx
