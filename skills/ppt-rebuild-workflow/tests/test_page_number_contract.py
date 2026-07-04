from __future__ import annotations

import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import calibrate_reference_render as calibrate  # noqa: E402
import make_reference_render_comparison as comparison  # noqa: E402
from _image_common import extract_page_number  # noqa: E402


class PageNumberContractTests(unittest.TestCase):
    """P2-1 / P4-2: calibrate and make_comparison must derive the same page."""

    FILENAMES = [
        "page-01.png",
        "slide-2-render.png",
        "p03.png",
        "render-7.png",
        "reference-10.png",
        "deck-2024-slide-05.png",  # label wins over the stray year number
        "final.png",  # no number -> None
        "shot-2-3.png",  # ambiguous multi-number, no label -> None
    ]

    def test_shared_helper_is_label_first(self) -> None:
        cases = {
            "page-01.png": 1,
            "slide-2-render.png": 2,
            "p03.png": 3,
            "render-7.png": 7,
            "deck-2024-slide-05.png": 5,
            "final.png": None,
            "shot-2-3.png": None,
        }
        for name, expected in cases.items():
            self.assertEqual(extract_page_number(Path(name)), expected, name)

    def test_both_scripts_use_the_same_strategy(self) -> None:
        # calibrate.render_map and comparison rely on the same helper, so the
        # per-file mapping must be identical for every filename.
        for name in self.FILENAMES:
            path = Path(name)
            self.assertEqual(
                extract_page_number(path),
                comparison.extract_page_number(path, {}),
                name,
            )
            self.assertIs(calibrate.extract_page_number, comparison.extract_page_number)


if __name__ == "__main__":
    unittest.main()
