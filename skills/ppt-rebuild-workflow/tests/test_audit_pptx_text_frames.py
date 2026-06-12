from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from audit_pptx_text_frames import audit  # noqa: E402
from tests.common import (  # noqa: E402
    make_connector_pptx,
    make_inherited_placeholder_pptx,
    make_slide_layout_relationship_absolute,
    make_rotation_and_group_pptx,
)


class AuditPptxTextFramesTests(unittest.TestCase):
    def test_connector_crossing_text_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pptx = make_connector_pptx(Path(directory) / "connector.pptx")

            result = audit(pptx, body_min_chars=45, min_overlap_px=1.0)

        self.assertEqual(result["totals"]["connectorCount"], 1)
        self.assertGreater(
            result["totals"]["thinShapeTextFrameIntersections"],
            0,
        )

    def test_inherits_placeholder_frames_from_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pptx = make_inherited_placeholder_pptx(Path(directory) / "placeholder.pptx")

            result = audit(pptx, body_min_chars=45, min_overlap_px=1.0)

        self.assertEqual(result["pages"][0]["textShapeCount"], 2)
        self.assertEqual(result["pages"][0]["directFrameCount"], 0)
        self.assertEqual(result["pages"][0]["inheritedFrameCount"], 2)

    def test_rotation_and_group_transform_coverage_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pptx = make_rotation_and_group_pptx(Path(directory) / "geometry.pptx")

            result = audit(pptx, body_min_chars=45, min_overlap_px=1.0)

        totals = result["totals"]
        self.assertGreaterEqual(totals["rotationAdjustedShapeCount"], 1)
        self.assertGreaterEqual(
            totals["groupTransformResolvedCount"]
            + totals["unresolvedGroupTransformCount"],
            1,
        )
        self.assertIn("geometryCoverageRisks", result["pages"][0])

    def test_accepts_absolute_package_relationship_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pptx = make_inherited_placeholder_pptx(Path(directory) / "absolute.pptx")
            make_slide_layout_relationship_absolute(pptx)

            result = audit(pptx, body_min_chars=45, min_overlap_px=1.0)

        self.assertEqual(result["pages"][0]["inheritedFrameCount"], 2)


if __name__ == "__main__":
    unittest.main()
