from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "calibrate_reference_render.py"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import calibrate_reference_render as cr  # noqa: E402  (needs scripts on sys.path)


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

    def test_cli_survives_gbk_stdout_with_non_ascii_output_path(self) -> None:
        # Regression for P1-3: printing a non-GBK-encodable output path must not
        # crash on a GBK console (make_stdout_robust reconfigures stdout).
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference-01.png"
            render = root / "render-01.png"
            draw_scene(reference)
            draw_scene(render, 4, 3)
            measurements = root / "measurements.json"
            measurements.write_text(json.dumps(measurement(reference)), encoding="utf-8")
            output = root / "calibration-\U0001F3AF.json"
            environment = os.environ.copy()
            environment["PYTHONIOENCODING"] = "gbk"
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
                env=environment,
                check=False,
            )
            output_exists = output.exists()
        self.assertEqual(result.returncode, 0, result.stderr.decode("gbk", "backslashreplace"))
        self.assertNotIn(b"UnicodeEncodeError", result.stderr)
        self.assertTrue(output_exists)

    def test_no_cv2_numpy_branch_matches_known_translation(self) -> None:
        # P0-1 / P4-1: with cv2 forced off, the vectorized numpy matcher must
        # recover the same known (dx, dy) translation as the former loop.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference-01.png"
            render = root / "render-01.png"
            draw_scene(reference)
            draw_scene(render, 4, 3)
            page = measurement(reference)["pages"][0]
            overlay_dir = root / "overlays"
            saved_cv2 = cr.cv2
            cr.cv2 = None
            try:
                result = cr.analyze_page(
                    page,
                    render,
                    overlay_dir,
                    tolerance=6.0,
                    search_radius=8,
                    minimum_matches=3,
                )
            finally:
                cr.cv2 = saved_cv2
        offsets = {(item["dx"], item["dy"]) for item in result["anchorMatches"]}
        self.assertIn((4, 3), offsets)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(any(item.get("engine") == "numpy" for item in result["anchorMatches"]))

    def test_pure_python_fallback_matches_known_translation(self) -> None:
        # Forces both cv2 and numpy off to exercise the edge_points + match_anchor
        # fallback (previously untested) and validate the membership-count refactor.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference-01.png"
            render = root / "render-01.png"
            draw_scene(reference)
            draw_scene(render, 4, 3)
            page = measurement(reference)["pages"][0]
            overlay_dir = root / "overlays"
            saved_np, saved_cv2 = cr.np, cr.cv2
            cr.np = None
            cr.cv2 = None
            try:
                result = cr.analyze_page(
                    page,
                    render,
                    overlay_dir,
                    tolerance=6.0,
                    search_radius=8,
                    minimum_matches=3,
                )
            finally:
                cr.np, cr.cv2 = saved_np, saved_cv2
        offsets = {(item["dx"], item["dy"]) for item in result["anchorMatches"]}
        self.assertIn((4, 3), offsets)
        self.assertEqual(result["status"], "PASS")

    def test_verbose_adds_stderr_without_changing_stdout(self) -> None:
        # P2-6: --verbose prints tolerance derivation to stderr; stdout (the
        # output-path contract) is unchanged.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference-01.png"
            render = root / "render-01.png"
            draw_scene(reference)
            draw_scene(render, 4, 3)
            measurements = root / "measurements.json"
            measurements.write_text(json.dumps(measurement(reference)), encoding="utf-8")
            plain_out = root / "plain.json"
            verbose_out = root / "verbose.json"
            base = [sys.executable, str(SCRIPT), str(measurements), str(render), "--search-radius", "8"]
            plain = subprocess.run(
                base + ["--output", str(plain_out)], capture_output=True, text=True, check=False
            )
            verbose = subprocess.run(
                base + ["--output", str(verbose_out), "--verbose"],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(plain.returncode, verbose.returncode)
        self.assertEqual(plain.stdout.strip(), str(plain_out))
        self.assertEqual(verbose.stdout.strip(), str(verbose_out))
        self.assertIn("tolerancePx", verbose.stderr)
        self.assertNotIn("tolerancePx", plain.stderr)

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
