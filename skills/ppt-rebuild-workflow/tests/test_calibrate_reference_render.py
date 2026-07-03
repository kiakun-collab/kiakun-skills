from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "calibrate_reference_render.py"


def draw_scene(path: Path, dx: int = 0, dy: int = 0) -> None:
    image = Image.new("RGB", (320, 180), "white")
    draw = ImageDraw.Draw(image)
    for box in ((20, 20, 120, 70), (170, 25, 295, 85), (45, 110, 270, 155)):
        shifted = tuple(
            value + (dx if index % 2 == 0 else dy)
            for index, value in enumerate(box)
        )
        draw.rectangle(shifted, outline="black", width=3)
    image.save(path)


def measurement(path: Path, anchor_count: int = 3) -> dict:
    boxes = (
        {"x": 20, "y": 20, "w": 101, "h": 51},
        {"x": 170, "y": 25, "w": 126, "h": 61},
        {"x": 45, "y": 110, "w": 226, "h": 46},
    )
    return {
        "pages": [
            {
                "page": 1,
                "image": str(path),
                "coordinateSystem": {"width": 320, "height": 180},
                "coordinateTransform": {
                    "sourcePxToCanvas": {"scaleX": 1, "scaleY": 1, "offsetX": 0, "offsetY": 0}
                },
                "autoAnchors": [
                    {"id": f"anchor-{index+1:02d}", "kind": "region", "bbox": box}
                    for index, box in enumerate(boxes[:anchor_count])
                ],
            }
        ]
    }


class CalibrateReferenceRenderTests(unittest.TestCase):
    def test_measures_known_translation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference-01.png"
            render = root / "render-01.png"
            draw_scene(reference)
            draw_scene(render, 4, 3)
            measurements = root / "measurements.json"
            measurements.write_text(json.dumps(measurement(reference)), encoding="utf-8")
            output = root / "calibration.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(measurements),
                    str(render),
                    "--output",
                    str(output),
                    "--search-radius",
                    "8",
                    "--tolerance-px",
                    "6",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            data = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(data["status"], "PASS")
        offsets = {(item["dx"], item["dy"]) for item in data["pages"][0]["anchorMatches"]}
        self.assertIn((4, 3), offsets)

    def test_insufficient_matches_cannot_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference-01.png"
            render = root / "render-01.png"
            draw_scene(reference)
            draw_scene(render)
            measurements = root / "measurements.json"
            measurements.write_text(json.dumps(measurement(reference, 1)), encoding="utf-8")
            output = root / "calibration.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(measurements),
                    str(render),
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            data = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(data["status"], "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
