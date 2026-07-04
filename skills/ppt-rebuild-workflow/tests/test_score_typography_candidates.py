from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "score_typography_candidates.py"


def render_candidate(path: Path, clipped: bool) -> None:
    image = Image.new("RGB", (160, 60), "white")
    draw = ImageDraw.Draw(image)
    draw.text((0 if clipped else 12, 0 if clipped else 18), "Candidate", fill="black")
    image.save(path)


class ScoreTypographyCandidatesTests(unittest.TestCase):
    def test_selects_non_clipping_candidate_with_matching_line_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            render_candidate(root / "good.png", False)
            render_candidate(root / "bad.png", True)
            data = {
                "items": [
                    {
                        "id": "title",
                        "reference": {
                            "glyphBBox": {"x": 0, "y": 0, "w": 50, "h": 10},
                            "lineCount": 1,
                            "lineGapPx": None,
                        },
                        "candidates": [
                            {
                                "id": "good",
                                "renderPath": "good.png",
                                "renderCrop": {"x": 0, "y": 0, "w": 160, "h": 60},
                                "fontFamily": "Arial",
                                "fontSizePt": 18,
                            },
                            {
                                "id": "bad",
                                "renderPath": "bad.png",
                                "renderCrop": {"x": 0, "y": 0, "w": 160, "h": 60},
                                "fontFamily": "Arial",
                                "fontSizePt": 24,
                            },
                        ],
                    }
                ]
            }
            source = root / "input.json"
            output = root / "output.json"
            source.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(source), "--output", str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            scored = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(scored["items"][0]["selected"]["candidateId"], "good")
        self.assertEqual(scored["generatedBy"], "score_typography_candidates.py")


    def test_single_bad_item_is_recorded_without_aborting(self) -> None:
        # P2-3 / P4-4: a malformed item is recorded in failures; the valid item
        # is still scored and the run exits 1 (FAIL) rather than 2 (crash).
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            render_candidate(root / "good.png", False)
            data = {
                "items": [
                    {
                        "id": "title",
                        "reference": {
                            "glyphBBox": {"x": 0, "y": 0, "w": 50, "h": 10},
                            "lineCount": 1,
                            "lineGapPx": None,
                        },
                        "candidates": [
                            {
                                "id": "good",
                                "renderPath": "good.png",
                                "renderCrop": {"x": 0, "y": 0, "w": 160, "h": 60},
                                "fontFamily": "Arial",
                                "fontSizePt": 18,
                            }
                        ],
                    },
                    {"id": "bad-item", "candidates": ["not-a-mapping"]},
                ]
            }
            source = root / "input.json"
            output = root / "output.json"
            source.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(source), "--output", str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            scored = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(scored["status"], "FAIL")
        self.assertEqual(scored["items"][0]["selected"]["candidateId"], "good")
        self.assertTrue(any(item.get("itemId") == "bad-item" for item in scored["failures"]))


if __name__ == "__main__":
    unittest.main()
