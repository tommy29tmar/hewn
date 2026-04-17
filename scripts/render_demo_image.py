#!/usr/bin/env python3
"""Render assets/launch/demo.png — a clean, viral-friendly before/after.

Left: verbose Claude default (truncated with "...").
Right: Flint 6-line reply.
Bottom: headline numbers.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "launch" / "demo.png"

BG            = (14, 16, 22)
PANEL_BG      = (24, 28, 38)
SIGIL_BG      = (20, 30, 30)
BORDER        = (60, 66, 80)
SIGIL_BORDER  = (80, 200, 160)
TEXT_DIM      = (170, 176, 190)
TEXT_BRIGHT   = (230, 234, 245)
ACCENT        = (120, 220, 180)
ACCENT_WARN   = (240, 200, 110)
HEADLINE      = (255, 255, 255)

W, H = 1600, 900
PAD = 60
GAP = 40
PANEL_Y = 180
PANEL_H = 520
PANEL_W = (W - 2 * PAD - GAP) // 2

VERBOSE_BODY = """# Webhook Timestamp Skew Fix

## Diagnosis
Symmetric window `abs(now-ts) > 300` rejects
valid webhooks when the provider clock is
slightly ahead OR when edge node drifts.
Need asymmetric tolerance: generous for past
(network/retry delay), tight for future
(replay protection).

## Min Fix

```python
MAX_AGE = 300   # up to 5 min old
MAX_SKEW = 60   # provider clock ahead
delta = now - ts
if delta > MAX_AGE or delta < -MAX_SKEW:
    return 401
```

## Regression Test

  (...continues for 600+ more tokens)"""

SIGIL_BODY = """@flint v0 hybrid
G: fix_skew
C: webhook_verify ∧ "300" ∧ "401" ∧ edge_reject
P: widen_window ∧ provider_skew_only ∧ reg_test
V: valid_webhook_passes ∧ stale_still_401
A: patch_tolerance ∧ add_reg_test"""


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates_bold = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    candidates_regular = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in (candidates_bold if bold else candidates_regular):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_panel(draw, x, y, w, h, bg, border, radius=18):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=bg, outline=border, width=2)


def main() -> None:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Header
    draw.text((PAD, 50),
        "Flint vs default Claude — same question, Opus 4.7",
        fill=HEADLINE, font=_font(40, bold=True))
    draw.text((PAD, 110),
        "Fix a webhook that rejects valid events when abs(now-ts) > 300 returns 401.",
        fill=TEXT_DIM, font=_font(22))

    # Left panel — verbose default
    lx, ly = PAD, PANEL_Y
    draw_panel(draw, lx, ly, PANEL_W, PANEL_H, PANEL_BG, BORDER)
    draw.text((lx + 28, ly + 24), "Claude (default)", fill=TEXT_BRIGHT, font=_font(28, bold=True))
    draw.text((lx + 28, ly + 64), "905 tokens · 12.4s",
              fill=ACCENT_WARN, font=_font(22, bold=True))
    body_font = _font(18)
    ty = ly + 115
    for line in VERBOSE_BODY.split("\n"):
        if ty > ly + PANEL_H - 40:
            break
        draw.text((lx + 28, ty), line, fill=TEXT_DIM, font=body_font)
        ty += 26

    # Right panel — Flint
    rx, ry = PAD + PANEL_W + GAP, PANEL_Y
    draw_panel(draw, rx, ry, PANEL_W, PANEL_H, SIGIL_BG, SIGIL_BORDER)
    draw.text((rx + 28, ry + 24), "Claude + Flint",
              fill=ACCENT, font=_font(28, bold=True))
    draw.text((rx + 28, ry + 64), "415 tokens · 3.3s",
              fill=ACCENT, font=_font(22, bold=True))
    sigil_font = _font(20)
    ty = ry + 125
    for line in SIGIL_BODY.split("\n"):
        draw.text((rx + 28, ty), line, fill=TEXT_BRIGHT, font=sigil_font)
        ty += 32

    # Bottom headline
    banner_y = PANEL_Y + PANEL_H + 40
    draw.text((PAD, banner_y),
        "-54% tokens   ·   -73% latency   ·   same concepts covered",
        fill=HEADLINE, font=_font(38, bold=True))
    draw.text((PAD, banner_y + 60),
        "Averaged over 4 runs × 8 technical tasks. One /flint install in Claude Code.",
        fill=TEXT_DIM, font=_font(20))

    img.save(OUT, "PNG", optimize=True)
    print(f"wrote {OUT} — {OUT.stat().st_size // 1024} KB, {Image.open(OUT).size}")


if __name__ == "__main__":
    main()
