from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "make_reference_render_comparison.py"
)


def write_image(path: Path) -> None:
    Image.new("RGB", (64, 36), "#446688").save(path)


def run_comparison(reference_dir: Path, render_dir: Path, output: Path) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(reference_dir),
            str(render_dir),
            str(output),
        ],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )


class MakeReferenceRenderComparisonTests(unittest.TestCase):
    def test_rejects_mismatched_page_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            references = root / "references"
            renders = root / "renders"
            references.mkdir()
            renders.mkdir()
            write_image(references / "page-01.png")
            write_image(references / "page-02.png")
            write_image(renders / "page-02.png")
            write_image(renders / "page-03.png")

            result = run_comparison(references, renders, root / "comparison.png")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing render pages: 1", result.stderr)
        self.assertIn("Extra render pages: 3", result.stderr)

    def test_rejects_duplicate_page_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            references = root / "references"
            renders = root / "renders"
            references.mkdir()
            renders.mkdir()
            write_image(references / "page-01.png")
            write_image(references / "slide-01.png")
            write_image(renders / "page-01.png")

            result = run_comparison(references, renders, root / "comparison.png")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Duplicate reference page: 1", result.stderr)

    def test_writes_pairing_manifest_for_matching_pages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            references = root / "references"
            renders = root / "renders"
            references.mkdir()
            renders.mkdir()
            for page in (1, 2):
                write_image(references / f"page-{page:02d}.png")
                write_image(renders / f"slide-{page:02d}.png")
            output = root / "comparison.png"

            result = run_comparison(references, renders, output)
            manifest_path = root / "comparison.pairing.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            output_exists = output.exists()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(output_exists)
        self.assertEqual([item["page"] for item in manifest["pairings"]], [1, 2])
        self.assertEqual(manifest["pairings"][0]["reference"], "page-01.png")
        self.assertEqual(manifest["pairings"][0]["render"], "slide-01.png")


if __name__ == "__main__":
    unittest.main()
