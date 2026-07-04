#!/usr/bin/env python3
"""Create a page-number-validated reference-vs-render comparison sheet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow is required: install it with `python -m pip install Pillow`.") from exc

from _image_common import (
    IMAGE_EXTENSIONS,
    extract_page_number,
    load_image_rgb,
    load_overlay_font,
    natural_key,
)
from _io_common import write_json


def image_files(directory: Path) -> list[Path]:
    return sorted(
        [
            path
            for path in directory.iterdir()
            if path.suffix.lower() in IMAGE_EXTENSIONS
            and not path.name.startswith("_")
            and "contact-sheet" not in path.name.lower()
            and "contact_sheet" not in path.name.lower()
        ],
        key=natural_key,
    )


def load_manifest(path: Path | None) -> dict[str, dict[str, int]]:
    if path is None:
        return {"references": {}, "renders": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "references": {
            str(name): int(page) for name, page in data.get("references", {}).items()
        },
        "renders": {
            str(name): int(page) for name, page in data.get("renders", {}).items()
        },
    }


def page_map(
    files: list[Path],
    explicit: dict[str, int],
    label: str,
) -> dict[int, Path]:
    result: dict[int, Path] = {}
    for path in files:
        page = extract_page_number(path, explicit)
        if page is None:
            raise SystemExit(
                f"Cannot extract {label} page number from {path.name}; "
                "provide --manifest."
            )
        if page in result:
            raise SystemExit(f"Duplicate {label} page: {page}")
        result[page] = path
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create a reference-vs-render comparison sheet after validating "
            "page-number pairing."
        )
    )
    parser.add_argument("reference_dir")
    parser.add_argument("render_dir")
    parser.add_argument("output")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=360)
    parser.add_argument(
        "--manifest",
        help=(
            "Optional JSON mapping with references/renders filename-to-page objects, "
            "required when filenames have no reliable page number."
        ),
    )
    parser.add_argument(
        "--pairing-output",
        help="Optional pairing JSON path; defaults beside output as *.pairing.json.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help=(
            "Instead of failing on missing/extra pages, render a gray placeholder "
            "cell for the absent side and tag that pairing status=\"missing\"."
        ),
    )
    args = parser.parse_args()
    if args.width <= 0 or args.height <= 0:
        parser.error("--width and --height must be positive")

    reference_files = image_files(Path(args.reference_dir))
    render_files = image_files(Path(args.render_dir))
    if not reference_files and not render_files:
        raise SystemExit("No images found")
    manifest = load_manifest(Path(args.manifest) if args.manifest else None)
    references = page_map(reference_files, manifest["references"], "reference")
    renders = page_map(render_files, manifest["renders"], "render")
    missing_render_pages = sorted(set(references) - set(renders))
    extra_render_pages = sorted(set(renders) - set(references))
    if not args.allow_missing:
        errors = []
        if missing_render_pages:
            errors.append(
                "Missing render pages: " + ", ".join(str(page) for page in missing_render_pages)
            )
        if extra_render_pages:
            errors.append(
                "Extra render pages: " + ", ".join(str(page) for page in extra_render_pages)
            )
        if errors:
            raise SystemExit("; ".join(errors))
        pages = sorted(references)
    else:
        pages = sorted(set(references) | set(renders))

    width = args.width
    height = args.height
    label_height = 28
    gap = 12
    row_height = height + label_height + gap
    canvas = Image.new("RGB", (width * 2 + gap, row_height * len(pages)), "white")
    draw = ImageDraw.Draw(canvas)
    font = load_overlay_font()
    pairings = []

    def placeholder(text: str) -> Image.Image:
        cell = Image.new("RGB", (width, height), "#DDDDDD")
        ImageDraw.Draw(cell).text(
            (8, max(0, height // 2 - 6)), text, fill="#666666", font=font
        )
        return cell

    for row_index, page in enumerate(pages):
        reference_path = references.get(page)
        render_path = renders.get(page)
        try:
            reference = (
                load_image_rgb(reference_path).resize(
                    (width, height), Image.Resampling.LANCZOS
                )
                if reference_path is not None
                else placeholder("reference missing")
            )
            render = (
                load_image_rgb(render_path).resize(
                    (width, height), Image.Resampling.LANCZOS
                )
                if render_path is not None
                else placeholder("render missing")
            )
        except OSError as exc:
            print(f"image comparison failed on page {page}: {exc}", file=sys.stderr)
            return 2
        top = row_index * row_height
        canvas.paste(reference, (0, top + label_height))
        canvas.paste(render, (width + gap, top + label_height))
        draw.text((8, top + 7), f"Page {page:02d} reference", fill="black", font=font)
        draw.text(
            (width + gap + 8, top + 7),
            f"Page {page:02d} render",
            fill="black",
            font=font,
        )
        entry = {
            "page": page,
            "reference": reference_path.name if reference_path is not None else None,
            "render": render_path.name if render_path is not None else None,
        }
        if args.allow_missing:
            entry["status"] = (
                "matched" if reference_path is not None and render_path is not None else "missing"
            )
        pairings.append(entry)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)
    pairing_output = (
        Path(args.pairing_output)
        if args.pairing_output
        else output_path.with_suffix(".pairing.json")
    )
    write_json(
        pairing_output,
        {
            "referenceDirectory": str(Path(args.reference_dir)),
            "renderDirectory": str(Path(args.render_dir)),
            "output": str(output_path),
            "pairings": pairings,
        },
    )
    print(output_path)
    print(pairing_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
