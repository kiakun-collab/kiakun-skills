from __future__ import annotations

import sys
import unittest
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from _image_common import load_overlay_font  # noqa: E402


class OverlayFontTests(unittest.TestCase):
    """P2-2 / P4-3: overlay labels with CJK shape names must render, not crash."""

    def test_returns_a_usable_font(self) -> None:
        font = load_overlay_font()
        self.assertIsInstance(font, (ImageFont.ImageFont, ImageFont.FreeTypeFont))

    def test_draws_cjk_label_without_error(self) -> None:
        font = load_overlay_font()
        canvas = Image.new("RGB", (240, 60), "white")
        draw = ImageDraw.Draw(canvas)
        # A Chinese shape name as it might appear on an annotation overlay.
        draw.text((4, 4), "标题-主 body-text 副标题", fill="black", font=font)

    def test_prefers_a_truetype_font_when_the_platform_has_one(self) -> None:
        # On Windows/macOS/Linux CI with system CJK fonts installed, the probe
        # should resolve a real TrueType face rather than the bitmap default.
        font = load_overlay_font()
        if sys.platform.startswith("win"):
            self.assertIsInstance(font, ImageFont.FreeTypeFont)


if __name__ == "__main__":
    unittest.main()
