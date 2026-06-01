#!/usr/bin/env python3
"""Slice a fixed-grid transparent sprite sheet into normalized PNG assets."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from PIL import Image


def parse_names(value: str) -> list[str]:
    names = [part.strip() for part in value.split(",") if part.strip()]
    if not names:
        raise argparse.ArgumentTypeError("--names must contain at least one name")
    return names


def alpha_bbox(image: Image.Image, threshold: int) -> tuple[int, int, int, int] | None:
    alpha = image.getchannel("A")
    mask = alpha.point(lambda pixel: 255 if pixel > threshold else 0)
    return mask.getbbox()


def normalize_cell(
    cell: Image.Image,
    canvas_size: int,
    max_subject: int,
    alpha_threshold: int,
) -> Image.Image:
    rgba = cell.convert("RGBA")
    bbox = alpha_bbox(rgba, alpha_threshold)
    output = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    if bbox is None:
        return output

    subject = rgba.crop(bbox)
    scale = min(max_subject / subject.width, max_subject / subject.height, 1.0)
    new_size = (
        max(1, round(subject.width * scale)),
        max(1, round(subject.height * scale)),
    )
    subject = subject.resize(new_size, Image.Resampling.LANCZOS)
    output.alpha_composite(subject, ((canvas_size - new_size[0]) // 2, (canvas_size - new_size[1]) // 2))
    return output


def slice_sheet(
    source: Path,
    out_dir: Path,
    cols: int,
    rows: int,
    names: Iterable[str],
    canvas_size: int,
    max_subject: int,
    alpha_threshold: int,
) -> list[Path]:
    names = list(names)
    expected = cols * rows
    if len(names) != expected:
        raise ValueError(f"expected {expected} names for {cols}x{rows}, got {len(names)}")

    image = Image.open(source).convert("RGBA")
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for index, name in enumerate(names):
        col = index % cols
        row = index // cols
        box = (
            round(col * image.width / cols),
            round(row * image.height / rows),
            round((col + 1) * image.width / cols),
            round((row + 1) * image.height / rows),
        )
        cell = image.crop(box)
        final = normalize_cell(cell, canvas_size, max_subject, alpha_threshold)
        dest = out_dir / f"{name}.png"
        final.save(dest)
        written.append(dest)

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Transparent/cutout source sheet")
    parser.add_argument("--out", required=True, type=Path, help="Output directory")
    parser.add_argument("--cols", required=True, type=int)
    parser.add_argument("--rows", required=True, type=int)
    parser.add_argument("--names", required=True, type=parse_names, help="Comma-separated output names")
    parser.add_argument("--size", type=int, default=256, help="Final square canvas size")
    parser.add_argument("--max-subject", type=int, default=220, help="Max subject width/height inside canvas")
    parser.add_argument("--alpha-threshold", type=int, default=12, help="Alpha threshold for subject bbox")
    args = parser.parse_args()

    if args.cols <= 0 or args.rows <= 0:
        raise SystemExit("--cols and --rows must be positive")
    if args.size <= 0 or args.max_subject <= 0:
        raise SystemExit("--size and --max-subject must be positive")
    if args.max_subject > args.size:
        raise SystemExit("--max-subject must be <= --size")

    written = slice_sheet(
        args.input,
        args.out,
        args.cols,
        args.rows,
        args.names,
        args.size,
        args.max_subject,
        args.alpha_threshold,
    )
    print(f"Wrote {len(written)} assets to {args.out}")


if __name__ == "__main__":
    main()
