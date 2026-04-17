"""Smoke test: ensure scripts/*.py entry points import cleanly after rebrand sweeps."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestScriptsImport(unittest.TestCase):
    def setUp(self) -> None:
        self._src_path_added = False
        src_dir = str(ROOT / "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
            self._src_path_added = True

    def tearDown(self) -> None:
        if self._src_path_added:
            src_dir = str(ROOT / "src")
            if src_dir in sys.path:
                sys.path.remove(src_dir)

    def test_table_scripts_import(self) -> None:
        for name in (
            "opus_opt_table.py",
            "opus_long_table.py",
            "skill_ab_table.py",
            "caveman_table.py",
        ):
            path = ROOT / "scripts" / name
            with self.subTest(script=name):
                _load(path)


if __name__ == "__main__":
    unittest.main()
