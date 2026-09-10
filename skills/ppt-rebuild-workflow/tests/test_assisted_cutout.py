from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image, ImageDraw

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from extract_asset_grabcut import extract


class AssistedCutoutTests(unittest.TestCase):
    def fixture(self, root):
        image = Image.new('RGB', (180, 140), '#ececec')
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 89, 139), fill='#ccddee')
        draw.rectangle((30, 30, 100, 110), fill='#c52731')
        draw.rectangle((50, 45, 70, 65), fill='white')  # A white marking, not background.
        draw.rectangle((55, 80, 70, 100), fill='#ccddee')  # A background opening.
        draw.rectangle((125, 40, 145, 60), fill='#d2a430')  # Disconnected small accessory.
        path = root / 'source.png'
        image.save(path)
        return path, {
            'sourceSize': [180, 140], 'roi': [10, 10, 170, 130],
            'foregroundPolygons': [[[30, 30], [100, 30], [100, 110], [30, 110]],
                                   [[125, 40], [145, 40], [145, 60], [125, 60]]],
            'backgroundPolygons': [[[55, 80], [70, 80], [70, 100], [55, 100]]],
            'excludePolygons': [], 'uncertaintyRadius': 3, 'edgeRadius': 0, 'padding': 12
        }

    def test_white_marking_hole_and_disconnected_accessory_survive_correctly(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, hints = self.fixture(Path(tmp))
            image, _, meta = extract(source, hints)
            x, y = meta['outputToSource']['translateX'], meta['outputToSource']['translateY']
            self.assertEqual(image.getpixel((60-x, 55-y)), (255, 255, 255, 255))
            self.assertEqual(image.getpixel((60-x, 90-y))[3], 0)
            self.assertEqual(image.getpixel((135-x, 50-y)), (210, 164, 48, 255))
            self.assertEqual(meta['componentCount'], 2)
            self.assertEqual(meta['visibleBBoxSource'], [30, 30, 146, 111])
            self.assertEqual(meta['outputToSource'], {'translateX': 18, 'translateY': 18})
            self.assertEqual(image.size, (140, 105))
            self.assertEqual(meta['visualStatus'], 'NOT_REVIEWED')

    def test_explicit_exclusion_stays_transparent_after_edge_refinement(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, hints = self.fixture(Path(tmp))
            hints['edgeRadius'] = 2
            hints['excludePolygons'] = [[[30, 30], [42, 30], [42, 42], [30, 42]]]
            image, _, meta = extract(source, hints)
            x, y = meta['outputToSource']['translateX'], meta['outputToSource']['translateY']
            self.assertEqual(image.getpixel((40-x, 40-y))[3], 0)
            self.assertEqual(image.getpixel((60-x, 55-y)), (255, 255, 255, 255))

    def test_existing_black_transparent_asset_is_reused_without_pixel_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'alpha.png'
            original = Image.new('RGBA', (80, 60), (0, 0, 0, 0))
            ImageDraw.Draw(original).rectangle((20, 10, 50, 40), fill=(0, 0, 0, 255))
            original.putpixel((19, 20), (15, 20, 25, 80))
            original.save(source)
            result, _, meta = extract(source, {'sourceSize': [80, 60]})
            np.testing.assert_array_equal(np.array(result), np.array(original))
            self.assertEqual(meta['method'], 'ALPHA_REUSED')
            self.assertEqual(meta['outputToSource'], {'translateX': 0, 'translateY': 0})

    def test_invalid_coordinates_and_empty_inputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, hints = self.fixture(Path(tmp))
            hints['sourceSize'] = [1280, 720]
            with self.assertRaises(ValueError):
                extract(source, hints)
            hints['sourceSize'] = [180, 140]
            hints['foregroundPolygons'][0][0] = [0, 0]
            with self.assertRaises(ValueError):
                extract(source, hints)
            Image.new('RGBA', (180, 140), (0, 0, 0, 0)).save(source)
            with self.assertRaises(ValueError):
                extract(source, hints)

    def test_cli_writes_reviewable_artifacts_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, hints = self.fixture(root)
            hints_path = root / 'hints.json'
            hints_path.write_text(json.dumps(hints), encoding='utf-8')
            output = root / 'v1'
            args = [sys.executable, '-B', str(SCRIPTS / 'extract_asset_grabcut.py'),
                    '--input', str(source), '--hints', str(hints_path), '--out-dir', str(output)]
            result = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(all((output / name).is_file() for name in ['asset.png', 'mask.png', 'preview.png', 'cutout.json']))
            before = (output / 'asset.png').read_bytes()
            result = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual((output / 'asset.png').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
