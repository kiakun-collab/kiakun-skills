from __future__ import annotations
import tempfile
import unittest
import sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_image_alpha import inspect_alpha, audit_assets


class AlphaTests(unittest.TestCase):
    def test_rgb_and_fully_opaque_rgba_are_not_cutouts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for mode in ("RGB", "RGBA"):
                path = root / (mode + ".png")
                Image.new(mode, (12, 12), "white").save(path)
                self.assertEqual(inspect_alpha(path)["status"], "OPAQUE")

    def test_alpha_is_measured_but_never_claims_edge_quality(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "asset.png"
            image = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
            image.putpixel((5, 5), (255, 20, 20, 255))
            image.save(path)
            result = inspect_alpha(path)
            self.assertEqual(result["status"], "ALPHA_PRESENT")
            self.assertEqual(result["edgeQuality"], "NOT_REVIEWED")
            self.assertAlmostEqual(result["transparentPixelRatio"], .99)

    def test_palette_transparency_is_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "palette.png"
            image = Image.new("P", (10, 10), 0)
            image.putpixel((2, 2), 1)
            image.save(path, transparency=0)
            self.assertEqual(inspect_alpha(path)["status"], "ALPHA_PRESENT")

    def test_manual_handoff_stops_alpha_regeneration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            Image.new("RGB", (12, 12), "white").save(root / "person.png")
            manifest = {"assets": [{"id": "person", "path": "person.png", "requiresAlpha": True}]}
            result = audit_assets(manifest, root)
            self.assertEqual(result["status"], "MANUAL_CUTOUT_REQUIRED")
            self.assertFalse(result["assets"][0]["regenerateForAlpha"])
            self.assertEqual(audit_assets(manifest, root, "required")["status"], "BLOCKED")
            manifest["assets"][0]["requiresAlpha"] = False
            self.assertEqual(audit_assets(manifest, root)["status"], "PASS")

    def test_empty_or_missing_images_cannot_be_handed_off_as_usable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            Image.new("RGBA", (12, 12), (0, 0, 0, 0)).save(root / "empty.png")
            for name in ("empty.png", "missing.png"):
                result = audit_assets({"assets": [{"id": "p", "path": name, "requiresAlpha": True}]}, root)
                self.assertEqual(result["status"], "BLOCKED")

    def test_ambiguous_manifest_is_rejected(self):
        with self.assertRaises(ValueError):
            audit_assets({"assets": [{"id": "p", "path": "x", "requiresAlpha": "false"}]}, Path("."))
