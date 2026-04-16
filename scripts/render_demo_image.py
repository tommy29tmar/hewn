#!/usr/bin/env python3
"""Render the demo output text into a clean PNG for the launch README."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Pillow not installed. pip install Pillow")

ROOT = Path(__file__).resolve().parents[1]

DEMO_TXT = ROOT / "assets" / "launch" / "demo_output.txt"
OUT_PNG = ROOT / "assets" / "launch" / "demo.png"


def find_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def main() -> int:
    text = DEMO_TXT.read_text(encoding="utf-8")
    # Strip ANSI sequences if present
    import re
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    lines = text.splitlines()

    font = find_font(14)
    bold_font = find_font(16)
    # Colors: terminal-like
    bg = (22, 25, 32)
    fg = (220, 223, 228)
    dim = (140, 146, 158)
    highlight = (140, 200, 120)    # green
    header = (220, 160, 80)        # amber

    # Compute image size
    max_w = max(len(line) for line in lines) if lines else 80
    char_w = 9  # approx
    line_h = 20
    pad = 24
    img_w = max(1100, pad * 2 + max_w * char_w)
    img_h = pad * 2 + len(lines) * line_h

    img = Image.new("RGB", (img_w, img_h), bg)
    draw = ImageDraw.Draw(img)

    y = pad
    for line in lines:
        color = fg
        use_font = font
        stripped = line.strip()
        if stripped.startswith(("1.", "2.", "3.", "Summary")):
            color = header
            use_font = bold_font
        elif stripped.startswith(("Model:", "Question:")):
            color = (140, 190, 220)  # blue-ish
            use_font = bold_font
        elif stripped.startswith("────"):
            color = dim
        elif "SIGIL" in line or "sigil" in line:
            if "-" in line and "%" in line:  # savings line
                color = highlight
        elif "vs terse" in line:
            if "-" in line:
                color = highlight
        elif stripped.startswith(("prompt:", "input:", "output:", "total:", "time:")):
            color = dim
        elif stripped.startswith("calling"):
            color = dim

        draw.text((pad, y), line, font=use_font, fill=color)
        y += line_h

    img.save(OUT_PNG, "PNG")
    print(f"wrote {OUT_PNG}  ({img_w}x{img_h})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
