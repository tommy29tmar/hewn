from __future__ import annotations

import unittest
from pathlib import Path

from sigil.context_prefix import compile_context_prefix, parse_handbook_sections
from sigil.metrics import approx_token_count


ROOT = Path(__file__).resolve().parents[1]


class ContextPrefixTests(unittest.TestCase):
    def test_parse_handbook_sections_extracts_known_headings(self) -> None:
        source = (ROOT / "evals" / "prefixes" / "service_context_v1.txt").read_text(encoding="utf-8")
        sections = parse_handbook_sections(source)
        self.assertIn("product snapshot", sections)
        self.assertIn("authentication and session rules", sections)
        self.assertIn("what not to do", sections)

    def test_cacheable_prefix_is_shorter_than_raw_and_keeps_key_literals(self) -> None:
        source = (ROOT / "evals" / "prefixes" / "service_context_v1.txt").read_text(encoding="utf-8")
        compiled = compile_context_prefix(source, category="debugging", style="cacheable")
        self.assertIn("[ctx cacheable debugging]", compiled)
        self.assertIn("`x-user-id`", compiled)
        self.assertIn("`401`", compiled)
        self.assertLess(approx_token_count(compiled), approx_token_count(source))
        self.assertGreater(approx_token_count(compiled), 500)

    def test_focused_prefix_is_shorter_than_cacheable(self) -> None:
        source = (ROOT / "evals" / "prefixes" / "service_context_v1.txt").read_text(encoding="utf-8")
        cacheable = compile_context_prefix(source, category="code_review", style="cacheable")
        focused = compile_context_prefix(source, category="code_review", style="focused")
        self.assertIn("[ctx focused code_review]", focused)
        self.assertLess(approx_token_count(focused), approx_token_count(cacheable))
        self.assertIn("spoof", focused.lower())


if __name__ == "__main__":
    unittest.main()
