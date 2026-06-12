#!/usr/bin/env python3
"""Create a page-number-validated reference-vs-render comparison sheet."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def natural_key(path: Path) -> list[object]:
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", path.name)
    ]


def image_files(directory: Path) -> list[Path]:
    allowed = {".png", ".jpg", ".jpeg", ".webp"}
    return sorted(
        [
            path
            for path in directory.iterdir()
            if path.suffix.lower() in allowed
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


def extract_page_number(path: Path, explicit: dict[str, int]) -> int | None:
    if path.name in explicit:
        return explicit[path.name]
    stem = path.stem
    labelled = re.search(r"(?:page|slide|p)[-_ ]*0*(\d+)(?!\d)", stem, re.IGNORECASE)
    if labelled:
        return int(labelled.group(1))
    numbers = re.findall(r"\d+", stem)
    if len(numbers) == 1:
        return int(numbers[0])
    return None


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
    args = parser.parse_args()

    reference_files = image_files(Path(args.reference_dir))
    render_files = image_files(Path(args.render_dir))
    if not reference_files and not render_files:
        raise SystemExit("No images found")
    manifest = load_manifest(Path(args.manifest) if args.manifest else None)
    references = page_map(reference_files, manifest["references"], "reference")
    renders = page_map(render_files, manifest["renders"], "render")
    missing_render_pages = sorted(set(references) - set(renders))
    extra_render_pages = sorted(set(renders) - set(references))
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
    width = args.width
    height = args.height
    label_height = 28
    gap = 12
    row_height = height + label_height + gap
    canvas = Image.new("RGB", (width * 2 + gap, row_height * len(pages)), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    pairings = []

    for row_index, page in enumerate(pages):
        reference_path = references[page]
        render_path = renders[page]
        with Image.open(reference_path) as reference_image:
            reference = reference_image.convert("RGB").resize(
                (width, height), Image.Resampling.LANCZOS
            )
        with Image.open(render_path) as render_image:
            render = render_image.convert("RGB").resize(
                (width, height), Image.Resampling.LANCZOS
            )
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
        pairings.append(
            {
                "page": page,
                "reference": reference_path.name,
                "render": render_path.name,
            }
        )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)
    pairing_output = (
        Path(args.pairing_output)
        if args.pairing_output
        else output_path.with_suffix(".pairing.json")
    )
    pairing_output.parent.mkdir(parents=True, exist_ok=True)
    pairing_output.write_text(
        json.dumps(
            {
                "referenceDirectory": str(Path(args.reference_dir)),
                "renderDirectory": str(Path(args.render_dir)),
                "output": str(output_path),
                "pairings": pairings,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(output_path)
    print(pairing_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
