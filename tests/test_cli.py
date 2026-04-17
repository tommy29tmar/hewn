from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from flint.cli import main


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_validate_command(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(["validate", str(ROOT / "examples" / "debugging.flint")])
        self.assertEqual(exit_code, 0)
        self.assertIn("OK:", buffer.getvalue())

    def test_audit_command(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(["audit", str(ROOT / "examples" / "architecture.flint")])
        self.assertEqual(exit_code, 0)
        self.assertIn("Default recommendation", buffer.getvalue())

    def test_stats_command(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(["stats", str(ROOT / "examples" / "debugging.flint"), "--json"])
        self.assertEqual(exit_code, 0)
        self.assertIn('"clause_count": 8', buffer.getvalue())

    def test_repair_command(self) -> None:
        path = ROOT / "tests" / "fixtures_repair_input.flint"
        path.write_text("@flint v0 hybrid\nP: try(await db_findUser) → next(err)\n[AUDIT]\nshort\n", encoding="utf-8")
        buffer = io.StringIO()
        try:
            with redirect_stdout(buffer):
                exit_code = main(["repair", str(path)])
            self.assertEqual(exit_code, 0)
            self.assertIn("await(db_findUser)", buffer.getvalue())
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
