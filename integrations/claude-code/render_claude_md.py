from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from flint.calibration import load_profile, render_claude_code_md  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a Claude Code CLAUDE.md from a calibrated Flint profile.")
    parser.add_argument("profile", type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--provider", default="anthropic")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    profile = load_profile(args.profile)
    rendered = render_claude_code_md(profile=profile, model=args.model, provider=args.provider)
    if args.out is None:
        print(rendered, end="")
        return 0
    args.out.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
