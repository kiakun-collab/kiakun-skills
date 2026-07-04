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


def run_comparison(
    reference_dir: Path,
    render_dir: Path,
    output: Path,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(reference_dir),
            str(render_dir),
            str(output),
            *(extra_args or []),
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


    def test_allow_missing_renders_placeholder_and_tags_status(self) -> None:
        # P2-5: --allow-missing degrades a missing render page to a placeholder
        # cell and tags that pairing status="missing" instead of hard-failing.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            references = root / "references"
            renders = root / "renders"
            references.mkdir()
            renders.mkdir()
            write_image(references / "page-01.png")
            write_image(references / "page-02.png")
            write_image(renders / "page-02.png")  # page 1 render is missing
            output = root / "comparison.png"

            result = run_comparison(references, renders, output, ["--allow-missing"])
            manifest_path = root / "comparison.pairing.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            output_exists = output.exists()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(output_exists)
        by_page = {item["page"]: item for item in manifest["pairings"]}
        self.assertEqual([1, 2], sorted(by_page))
        self.assertEqual(by_page[1]["status"], "missing")
        self.assertIsNone(by_page[1]["render"])
        self.assertEqual(by_page[2]["status"], "matched")
        self.assertEqual(by_page[2]["render"], "page-02.png")


if __name__ == "__main__":
    unittest.main()
