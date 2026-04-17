"""Tests for flint.claude_code: structural segmentation + whitespace-safe
compression + sha1 caching."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from flint.claude_code import (
    CompiledContext,
    cache_dir,
    cached_compile,
    compile_claude_md,
    safe_collapse_prose,
    segment_markdown,
)


FIXTURE = """\
# Project Instructions

Some free prose paragraph that should not be compressed.

## Rules

- Do not skip hooks
- When   editing    files,   preserve     order
- Use `pytest` to run tests
- /usr/local/bin/python

```bash
$ echo "hello"
```

A paragraph with `inline code`.

## Commands

$ make test

    ~/bin/tool --flag
"""


class SafeCollapseProseTests(unittest.TestCase):
    def test_collapses_internal_whitespace(self) -> None:
        self.assertEqual(safe_collapse_prose("  a    b   c  "), "a b c")

    def test_does_not_rewrite_words(self) -> None:
        self.assertEqual(safe_collapse_prose("Do not skip"), "Do not skip")
        self.assertEqual(safe_collapse_prose("X or Y"), "X or Y")

    def test_preserves_punctuation(self) -> None:
        self.assertEqual(safe_collapse_prose("a > b"), "a > b")
        self.assertEqual(safe_collapse_prose("k = v; q = r"), "k = v; q = r")


class SegmentMarkdownTests(unittest.TestCase):
    def test_headings_preserved(self) -> None:
        segs = segment_markdown("# Title\n## Sub\n")
        kinds = [s.kind for s in segs]
        self.assertEqual(kinds, ["heading", "heading"])
        for s in segs:
            self.assertTrue(s.preserved_verbatim)
            self.assertEqual(s.original_text, s.compressed_text)

    def test_fenced_code_byte_identical(self) -> None:
        src = "```bash\n$ echo hi\nmore\n```\n"
        segs = segment_markdown(src)
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0].kind, "fenced_code")
        self.assertEqual(segs[0].compressed_text, src)

    def test_do_not_rule_preserved_not_rewritten(self) -> None:
        src = "- Do not skip hooks\n"
        segs = segment_markdown(src)
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0].kind, "list_item_prose")
        self.assertIn("Do not skip hooks", segs[0].compressed_text)
        self.assertNotIn("Avoid skip hooks", segs[0].compressed_text)

    def test_list_item_whitespace_collapsed(self) -> None:
        src = "- When   editing    files,   preserve     order\n"
        segs = segment_markdown(src)
        self.assertEqual(segs[0].kind, "list_item_prose")
        self.assertNotEqual(segs[0].compressed_text, segs[0].original_text)
        self.assertIn("When editing files, preserve order", segs[0].compressed_text)

    def test_list_item_with_inline_code_preserved(self) -> None:
        src = "- Use `pytest` to run tests\n"
        segs = segment_markdown(src)
        self.assertEqual(segs[0].kind, "inline_code_paragraph")
        self.assertEqual(segs[0].compressed_text, src)

    def test_command_or_path_preserved(self) -> None:
        src = "$ make test\n"
        segs = segment_markdown(src)
        self.assertEqual(segs[0].kind, "command_or_path")
        self.assertEqual(segs[0].compressed_text, src)

    def test_concatenation_matches_original(self) -> None:
        segs = segment_markdown(FIXTURE)
        # Every original_text concatenated reproduces the input.
        rebuilt = "".join(s.original_text for s in segs)
        self.assertEqual(rebuilt, FIXTURE)


class CompileTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.path = self.tmp / "CLAUDE.md"
        self.path.write_text(FIXTURE)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_compile_claude_md_shrinks_whitespace_in_list_items(self) -> None:
        ctx = compile_claude_md(self.path)
        self.assertLess(len(ctx.compressed_text), len(ctx.original_text))
        self.assertIn("Do not skip hooks", ctx.compressed_text)
        self.assertIn("```bash", ctx.compressed_text)
        self.assertIn("$ echo", ctx.compressed_text)

    def test_compile_preserves_fenced_code_byte_identical(self) -> None:
        ctx = compile_claude_md(self.path)
        fenced = [s for s in ctx.segments if s.kind == "fenced_code"]
        self.assertEqual(len(fenced), 1)
        self.assertEqual(fenced[0].compressed_text, fenced[0].original_text)

    def test_cached_compile_hit_second_time(self) -> None:
        with tempfile.TemporaryDirectory() as cdir:
            os.environ["FLINT_CACHE_DIR"] = cdir
            try:
                self.assertEqual(str(cache_dir()), str(Path(cdir) / "claude-code"))
                ctx1 = cached_compile(self.path)
                cache_file = Path(cdir) / "claude-code" / f"{ctx1.hash}.md"
                self.assertTrue(cache_file.exists())
                marker = "\n# cache-hit-marker\n"
                cache_file.write_text(cache_file.read_text() + marker)
                ctx2 = cached_compile(self.path)
                self.assertIn(marker, ctx2.compressed_text)
                self.assertEqual(ctx1.hash, ctx2.hash)
            finally:
                os.environ.pop("FLINT_CACHE_DIR", None)

    def test_cache_miss_on_hash_change(self) -> None:
        with tempfile.TemporaryDirectory() as cdir:
            os.environ["FLINT_CACHE_DIR"] = cdir
            try:
                ctx1 = cached_compile(self.path)
                self.path.write_text(FIXTURE + "\n- extra bullet\n")
                ctx2 = cached_compile(self.path)
                self.assertNotEqual(ctx1.hash, ctx2.hash)
                self.assertIn("extra bullet", ctx2.compressed_text)
            finally:
                os.environ.pop("FLINT_CACHE_DIR", None)


if __name__ == "__main__":
    unittest.main()
