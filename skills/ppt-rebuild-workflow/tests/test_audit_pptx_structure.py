from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from audit_pptx_structure import audit

from tests.common import (
    add_explicit_run_fonts,
    make_basic_pptx,
    make_full_slide_picture_pptx,
    make_grouped_full_slide_picture_pptx,
    make_role_pptx,
)


class AuditPptxStructureTests(unittest.TestCase):
    def test_reports_all_font_slots_and_east_asian_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pptx = make_basic_pptx(Path(directory) / "font-mismatch.pptx")
            add_explicit_run_fonts(pptx, "TargetFont", "WrongEastAsianFont")

            result = audit(pptx)

        self.assertIn("TargetFont", result["latinFonts"])
        self.assertIn("WrongEastAsianFont", result["eastAsianFonts"])
        self.assertIn("ComplexFont", result["complexScriptFonts"])
        self.assertIn("SymbolFont", result["symbolFonts"])
        self.assertIn("WrongEastAsianFont", result["fontFamilies"])
        self.assertIn("themeFonts", result)
        self.assertIn("unresolvedInheritedFonts", result)

    def test_flags_full_slide_picture_even_with_small_text_overlays(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pptx = make_full_slide_picture_pptx(
                root / "full-slide.pptx", root / "background.png"
            )

            result = audit(pptx)

        self.assertEqual(result["fullSlideImageRiskPages"], [1])
        self.assertGreaterEqual(result["pages"][0]["maxPictureCoverageRatio"], 0.9)
        self.assertEqual(result["wholeReferenceImageEmbedded"]["status"], "risk")
        self.assertTrue(result["wholeReferenceImageEmbedded"]["manualEvidenceRequired"])

    def test_flags_full_slide_picture_inside_group(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pptx = make_grouped_full_slide_picture_pptx(
                root / "grouped-full-slide.pptx", root / "background.png"
            )
            result = audit(pptx)

        self.assertEqual(result["fullSlideImageRiskPages"], [1])
        self.assertGreaterEqual(result["pages"][0]["maxPictureCoverageRatio"], 0.9)
        self.assertEqual(result["pictureGeometryRisks"], [])

    def test_classifies_text_shapes_and_pictures_with_mutually_exclusive_roles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pptx = make_role_pptx(Path(directory) / "roles.pptx")

            result = audit(pptx)

        self.assertEqual(result["textShapeRoleCounts"]["title"], 1)
        self.assertEqual(result["textShapeRoleCounts"]["body-text"], 1)
        self.assertEqual(result["textShapeRoleCounts"]["page-number"], 1)
        self.assertEqual(result["textShapeRoleCounts"]["body-panel"], 1)
        self.assertEqual(result["pictureRoleCounts"]["content-image"], 1)
        self.assertNotIn("body-text-main", result["unknownRoleNames"])
        self.assertNotIn("title-main", result["unknownRoleNames"])

    def test_cli_survives_gbk_stdout_when_theme_contains_unicode_fonts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pptx = make_basic_pptx(root / "unicode-theme.pptx")
            environment = os.environ.copy()
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            environment["PYTHONIOENCODING"] = "gbk"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SKILL_ROOT / "scripts" / "audit_pptx_structure.py"),
                    str(pptx),
                    "--output",
                    str(root / "audit.json"),
                ],
                capture_output=True,
                env=environment,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr.decode("gbk"))

    def test_cli_reports_corrupt_pptx_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pptx = root / "corrupt.pptx"
            pptx.write_bytes(b"not a zip package")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SKILL_ROOT / "scripts" / "audit_pptx_structure.py"),
                    str(pptx),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("PPTX audit failed", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()
