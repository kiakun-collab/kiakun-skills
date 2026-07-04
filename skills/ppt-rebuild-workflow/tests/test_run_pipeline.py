from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tests.common import make_basic_pptx

SKILL_ROOT = Path(__file__).resolve().parents[1]
PIPELINE = SKILL_ROOT / "scripts" / "run_pipeline.py"


def write_reference(path: Path) -> None:
    image = Image.new("RGB", (640, 360), "white")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((60, 80, 360, 220), radius=12, fill="#DDEBFF", outline="#2266AA", width=3)
    draw.line((60, 260, 520, 260), fill="#333333", width=4)
    image.save(path)


class RunPipelineTests(unittest.TestCase):
    def test_pipeline_runs_available_steps_and_skips_inputless_ones(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            deck = make_basic_pptx(root / "deck.pptx")
            references = root / "references"
            renders = root / "renders"
            references.mkdir()
            renders.mkdir()
            write_reference(references / "page-01.png")
            write_reference(renders / "page-01.png")
            out = root / "out"
            result = subprocess.run(
                [
                    sys.executable,
                    str(PIPELINE),
                    str(deck),
                    "--reference-dir",
                    str(references),
                    "--renders-dir",
                    str(renders),
                    "--out-dir",
                    str(out),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            report = json.loads((out / "pipeline-report.json").read_text(encoding="utf-8"))
            measurements_exists = (out / "reference-measurements.json").exists()

        self.assertIn("pipeline-report.json", result.stdout)
        steps = {item["step"]: item for item in report["steps"]}
        self.assertEqual(steps["audit_structure"]["status"], "ok")
        self.assertEqual(steps["audit_text_frames"]["status"], "ok")
        self.assertEqual(steps["extract"]["status"], "ok")
        self.assertTrue(measurements_exists)
        # renders provided -> these steps actually run (ok or nonzero, not skipped)
        self.assertIn(steps["calibrate"]["status"], {"ok", "nonzero"})
        self.assertIn(steps["make_comparison"]["status"], {"ok", "nonzero"})
        # no inputs provided -> skipped, not failed
        self.assertEqual(steps["score_typography"]["status"], "skipped")
        self.assertEqual(steps["validate"]["status"], "skipped")

    def test_steps_subset_only_runs_requested(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            deck = make_basic_pptx(root / "deck.pptx")
            references = root / "references"
            references.mkdir()
            write_reference(references / "page-01.png")
            out = root / "out"
            subprocess.run(
                [
                    sys.executable,
                    str(PIPELINE),
                    str(deck),
                    "--reference-dir",
                    str(references),
                    "--out-dir",
                    str(out),
                    "--steps",
                    "audit_structure",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            report = json.loads((out / "pipeline-report.json").read_text(encoding="utf-8"))
        step_names = {item["step"] for item in report["steps"]}
        self.assertEqual(step_names, {"audit_structure"})


if __name__ == "__main__":
    unittest.main()
