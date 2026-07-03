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
    draw.rounded_rectangle(
        (60, 80, 360, 220),
        radius=12,
        fill="#DDEBFF",
        outline="#2266AA",
        width=3,
    )
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
            anchor_annotated_exists = Path(page["anchorAnnotatedImage"]).exists()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(data["settings"]["targetWidth"], 1280)
        self.assertEqual(data["settings"]["autoAnchorLimit"], 12)
        self.assertEqual(page["coordinateSystem"], {"width": 1280, "height": 720})
        self.assertEqual(page["coordinateTransform"]["sourcePxToCanvas"]["scaleX"], 2.0)
        self.assertEqual(page["coordinateTransform"]["sourcePxToCanvas"]["scaleY"], 2.0)
        self.assertTrue(page["autoAnchors"])
        self.assertEqual(page["autoAnchors"][0]["id"], "anchor-canvas-frame")
        self.assertTrue(page["dominantColors"])
        self.assertTrue(page["regionCandidates"])
        self.assertTrue(page["horizontalLineCandidates"])
        self.assertIn(page["anchorQuality"]["status"], {"PASS", "INSUFFICIENT"})
        self.assertIn(
            data["settings"]["measurementEngine"],
            {"opencv-numpy", "numpy-scipy", "python"},
        )
        self.assertTrue(annotated_exists)
        self.assertTrue(anchor_annotated_exists)

    def test_auto_fit_preserves_aspect_ratio_and_records_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = Image.new("RGB", (400, 400), "white")
            image.save(root / "square.png")
            output = root / "measurements.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(root / "square.png"), "--output", str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            data = json.loads(output.read_text(encoding="utf-8"))
        transform = data["pages"][0]["coordinateTransform"]
        self.assertEqual(result.returncode, 0)
        self.assertEqual(transform["fitMode"], "contain")
        self.assertEqual(
            transform["sourcePxToCanvas"]["scaleX"],
            transform["sourcePxToCanvas"]["scaleY"],
        )
        self.assertTrue(data["pages"][0]["warnings"])

    def test_bad_image_does_not_abort_valid_pages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "page-01.png").write_bytes(b"not an image")
            write_reference(root / "page-02.png")
            output = root / "measurements.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(root), "--output", str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            data = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(data["pages"]), 1)
        self.assertEqual(len(data["failedPages"]), 1)

    def test_rejects_zero_target_dimension(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_reference(root / "page.png")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(root / "page.png"),
                    "--output",
                    str(root / "out.json"),
                    "--target-width",
                    "0",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 2)

    def test_accelerated_and_python_engines_keep_geometry_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "page.png"
            write_reference(source)
            results = {}
            for engine in ("python", "numpy-scipy"):
                environment = os.environ.copy()
                environment["PPT_REBUILD_MEASUREMENT_ENGINE"] = engine
                output = root / f"{engine}.json"
                completed = subprocess.run(
                    [sys.executable, str(SCRIPT), str(source), "--output", str(output)],
                    capture_output=True,
                    text=True,
                    env=environment,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                results[engine] = json.loads(output.read_text(encoding="utf-8"))
        python_page = results["python"]["pages"][0]
        accelerated_page = results["numpy-scipy"]["pages"][0]
        self.assertEqual(
            python_page["coordinateTransform"],
            accelerated_page["coordinateTransform"],
        )
        first_python = python_page["horizontalLineCandidates"][0]["bbox"]
        first_accelerated = accelerated_page["horizontalLineCandidates"][0]["bbox"]
        for key in ("x", "y", "w", "h"):
            self.assertLessEqual(abs(first_python[key] - first_accelerated[key]), 1)


if __name__ == "__main__":
    unittest.main()
