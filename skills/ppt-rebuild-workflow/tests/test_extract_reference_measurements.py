from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "extract_reference_measurements.py"
)


def write_reference(path: Path) -> None:
    image = Image.new("RGB", (640, 360), "white")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((60, 80, 360, 220), radius=12, fill="#DDEBFF", outline="#2266AA", width=3)
    draw.line((60, 260, 520, 260), fill="#333333", width=4)
    draw.text((88, 120), "Title", fill="#111111")
    image.save(path)


class ExtractReferenceMeasurementsTests(unittest.TestCase):
    def test_writes_measurement_json_and_annotated_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            references = root / "references"
            references.mkdir()
            write_reference(references / "page-01.png")
            output = root / "measurements.json"
            annotated = root / "annotated"
            environment = os.environ.copy()
            environment["PYTHONDONTWRITEBYTECODE"] = "1"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(references),
                    "--output",
                    str(output),
                    "--annotated-dir",
                    str(annotated),
                ],
                capture_output=True,
                text=True,
                env=environment,
                check=False,
            )
            data = json.loads(output.read_text(encoding="utf-8"))
            page = data["pages"][0]
            annotated_exists = Path(page["annotatedImage"]).exists()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(data["settings"]["targetWidth"], 1280)
        self.assertEqual(data["settings"]["autoAnchorLimit"], 12)
        self.assertEqual(page["coordinateSystem"], {"w": 1280, "h": 720})
        self.assertEqual(page["coordinateTransform"]["sourcePxToCanvas"]["scaleX"], 2.0)
        self.assertEqual(page["coordinateTransform"]["sourcePxToCanvas"]["scaleY"], 2.0)
        self.assertTrue(page["autoAnchors"])
        self.assertEqual(page["autoAnchors"][0]["id"], "anchor-canvas-frame")
        self.assertTrue(page["dominantColors"])
        self.assertTrue(page["regionCandidates"])
        self.assertTrue(page["horizontalLineCandidates"])
        self.assertTrue(annotated_exists)


if __name__ == "__main__":
    unittest.main()
