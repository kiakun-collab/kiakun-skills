#!/usr/bin/env python3
"""Measure reference-to-render anchor offsets and emit computed calibration evidence."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow is required: install it with `python -m pip install Pillow`.") from exc

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

from _image_common import (
    IMAGE_EXTENSIONS,
    extract_page_number,
    load_image_rgb,
    load_overlay_font,
    percentile_from_histogram,
)
from _io_common import make_stdout_robust, write_json


def render_map(path: Path) -> dict[int, Path]:
    files = [path] if path.is_file() else sorted(
        item for item in path.iterdir() if item.suffix.lower() in IMAGE_EXTENSIONS
    )
    mapping: dict[int, Path] = {}
    if len(files) == 1 and extract_page_number(files[0]) is None:
        mapping[1] = files[0]
        return mapping
    for item in files:
        number = extract_page_number(item)
        if number is None:
            continue
        if number in mapping:
            raise ValueError(f"duplicate render page number {number}: {item}")
        mapping[number] = item
    return mapping


def fit_reference(path: Path, transform: dict, width: int, height: int) -> Image.Image:
    original = load_image_rgb(path)
    values = transform["sourcePxToCanvas"]
    scale_x = float(values["scaleX"])
    scale_y = float(values["scaleY"])
    offset_x = round(float(values.get("offsetX", 0)))
    offset_y = round(float(values.get("offsetY", 0)))
    resized = original.resize(
        (max(1, round(original.width * scale_x)), max(1, round(original.height * scale_y))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGB", (width, height), "white")
    canvas.paste(resized, (offset_x, offset_y))
    return canvas


def edge_points(image: Image.Image) -> set[tuple[int, int]]:
    edges = image.convert("L").filter(ImageFilter.FIND_EDGES)
    threshold = max(24, percentile_from_histogram(edges.histogram(), 0.9))
    pixels = edges.load()
    return {
        (x, y)
        for y in range(edges.height)
        for x in range(edges.width)
        if pixels[x, y] >= threshold
    }


def edge_array(image: Image.Image):
    if np is None:
        return None
    gray = np.asarray(image.convert("L"), dtype=np.uint8)
    if cv2 is not None:
        return cv2.Canny(gray, 40, 120)
    edges = np.asarray(image.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.uint8)
    threshold = max(24, int(np.percentile(edges, 90)))
    return (edges >= threshold).astype(np.uint8) * 255


def match_anchor_fast(reference, render, bbox: dict, search_radius: int) -> dict:
    height, width = reference.shape
    ref_left = max(0, int(bbox["x"]) - 2)
    ref_top = max(0, int(bbox["y"]) - 2)
    ref_right = min(width, int(bbox["x"] + bbox["w"]) + 2)
    ref_bottom = min(height, int(bbox["y"] + bbox["h"]) + 2)
    template = reference[ref_top:ref_bottom, ref_left:ref_right]
    search_left = max(0, ref_left - search_radius)
    search_top = max(0, ref_top - search_radius)
    search_right = min(width, ref_right + search_radius)
    search_bottom = min(height, ref_bottom + search_radius)
    search = render[search_top:search_bottom, search_left:search_right]
    reference_edges = int(np.count_nonzero(template))
    render_edges = int(np.count_nonzero(search))
    if reference_edges < 20 or render_edges < 20:
        return {"status": "UNMATCHED", "confidence": 0.0, "reason": "insufficient edges"}

    best_score, best_dx, best_dy = -1.0, 0, 0
    if (
        cv2 is not None
        and search.shape[0] >= template.shape[0]
        and search.shape[1] >= template.shape[1]
    ):
        scores = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
        _, best_score, _, location = cv2.minMaxLoc(scores)
        best_dx = search_left + location[0] - ref_left
        best_dy = search_top + location[1] - ref_top
    else:
        template_bool = template > 0
        for dy in range(-search_radius, search_radius + 1):
            for dx in range(-search_radius, search_radius + 1):
                left = ref_left + dx
                top = ref_top + dy
                right = left + template.shape[1]
                bottom = top + template.shape[0]
                if left < 0 or top < 0 or right > width or bottom > height:
                    continue
                candidate = render[top:bottom, left:right] > 0
                intersection = int(np.count_nonzero(template_bool & candidate))
                score = 2 * intersection / max(
                    1, reference_edges + int(np.count_nonzero(candidate))
                )
                if score > best_score:
                    best_score, best_dx, best_dy = score, dx, dy
    return {
        "status": "MATCHED" if best_score >= 0.12 else "UNMATCHED",
        "dx": int(best_dx),
        "dy": int(best_dy),
        "offsetPx": round(math.hypot(best_dx, best_dy), 3),
        "confidence": round(float(best_score), 4),
        "referenceEdgeCount": reference_edges,
        "renderEdgeCount": render_edges,
        "engine": "opencv-numpy" if cv2 is not None else "numpy",
    }


def crop_points(
    points: set[tuple[int, int]],
    bbox: dict,
    padding: int,
    width: int,
    height: int,
) -> set[tuple[int, int]]:
    left = max(0, int(bbox["x"]) - padding)
    top = max(0, int(bbox["y"]) - padding)
    right = min(width, int(bbox["x"] + bbox["w"]) + padding)
    bottom = min(height, int(bbox["y"] + bbox["h"]) + padding)
    return {(x, y) for x, y in points if left <= x < right and top <= y < bottom}


def match_anchor(
    reference_points: set[tuple[int, int]],
    render_points: set[tuple[int, int]],
    bbox: dict,
    width: int,
    height: int,
    search_radius: int,
) -> dict:
    reference = crop_points(reference_points, bbox, 2, width, height)
    render_window = crop_points(render_points, bbox, search_radius + 2, width, height)
    if len(reference) < 20 or len(render_window) < 20:
        return {"status": "UNMATCHED", "confidence": 0.0, "reason": "insufficient edges"}

    # The denominator is constant across offsets, so ranking by score is ranking
    # by raw intersection count. Counting membership directly avoids rebuilding a
    # shifted set on every offset (~2.5x faster, identical result and tie-break).
    best = (-1.0, 0, 0)
    denominator = max(1, len(reference) + len(render_window))
    reference_list = list(reference)
    for dy in range(-search_radius, search_radius + 1):
        for dx in range(-search_radius, search_radius + 1):
            intersection = sum(
                1 for x, y in reference_list if (x + dx, y + dy) in render_window
            )
            score = 2 * intersection / denominator
            if score > best[0]:
                best = (score, dx, dy)
    confidence, dx, dy = best
    return {
        "status": "MATCHED" if confidence >= 0.12 else "UNMATCHED",
        "dx": dx,
        "dy": dy,
        "offsetPx": round(math.hypot(dx, dy), 3),
        "confidence": round(confidence, 4),
        "referenceEdgeCount": len(reference),
        "renderEdgeCount": len(render_window),
    }


def analyze_page(
    page: dict,
    render_path: Path,
    overlay_dir: Path,
    tolerance: float,
    search_radius: int,
    minimum_matches: int,
) -> dict:
    coordinate_system = page.get("coordinateSystem", {})
    width = int(coordinate_system.get("width", coordinate_system.get("w", 0)))
    height = int(coordinate_system.get("height", coordinate_system.get("h", 0)))
    if width <= 0 or height <= 0:
        raise ValueError("coordinateSystem dimensions must be positive")
    reference = fit_reference(
        Path(page["image"]), page["coordinateTransform"], width, height
    )
    render = load_image_rgb(render_path)
    warnings = []
    if render.size != (width, height):
        warnings.append(
            f"render resized from {render.width}x{render.height} to {width}x{height}"
        )
        render = render.resize((width, height), Image.Resampling.LANCZOS)

    reference_array = edge_array(reference)
    render_array = edge_array(render)
    reference_points = edge_points(reference) if reference_array is None else None
    render_points = edge_points(render) if render_array is None else None
    matches = []
    for anchor in page.get("autoAnchors", []):
        if anchor.get("kind") == "canvas-frame":
            continue
        if reference_array is not None and render_array is not None:
            result = match_anchor_fast(
                reference_array, render_array, anchor["bbox"], search_radius
            )
        else:
            result = match_anchor(
                reference_points,
                render_points,
                anchor["bbox"],
                width,
                height,
                search_radius,
            )
        matches.append({"anchorId": anchor.get("id"), "bbox": anchor["bbox"], **result})

    valid = [item for item in matches if item["status"] == "MATCHED"]
    max_offset = max((item["offsetPx"] for item in valid), default=None)
    if len(valid) < minimum_matches:
        status = "INCONCLUSIVE"
    elif max_offset is not None and max_offset <= tolerance:
        status = "PASS"
    else:
        status = "FAIL"

    overlay = Image.blend(reference, render, 0.5)
    draw = ImageDraw.Draw(overlay)
    font = load_overlay_font()
    for item in matches:
        bbox = item["bbox"]
        left, top = bbox["x"], bbox["y"]
        right, bottom = left + bbox["w"], top + bbox["h"]
        color = "#00B86B" if item["status"] == "MATCHED" else "#E53935"
        draw.rectangle((left, top, right, bottom), outline=color, width=2)
        label = f"{item['anchorId']} {item.get('dx', '?')},{item.get('dy', '?')}"
        draw.text((left + 2, max(0, top - 12)), label, fill=color, font=font)
    overlay_dir.mkdir(parents=True, exist_ok=True)
    overlay_path = overlay_dir / f"page-{int(page['page']):02d}-calibration.png"
    overlay.save(overlay_path)
    return {
        "page": page["page"],
        "referenceImage": page["image"],
        "renderImage": str(render_path),
        "status": status,
        "tolerancePx": tolerance,
        "maxAnchorOffsetPx": max_offset,
        "matchedAnchorCount": len(valid),
        "minimumMatchedAnchors": minimum_matches,
        "anchorMatches": matches,
        "calibrationOverlay": str(overlay_path),
        "warnings": warnings,
        "calibrationEngine": "opencv-numpy" if cv2 is not None and np is not None else "python",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("measurements", help="reference-measurements.json")
    parser.add_argument("renders", help="Rendered PNG file or directory")
    parser.add_argument("--output", required=True)
    parser.add_argument("--overlay-dir")
    parser.add_argument("--tolerance-px", type=float)
    parser.add_argument("--search-radius", type=int, default=12)
    parser.add_argument("--minimum-matches", type=int, default=3)
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print tolerance derivation and render/page count warnings to stderr.",
    )
    args = parser.parse_args()
    if args.search_radius < 1 or args.minimum_matches < 1:
        parser.error("search radius and minimum matches must be positive")

    measurements_path = Path(args.measurements)
    output_path = Path(args.output)
    overlay_dir = (
        Path(args.overlay_dir)
        if args.overlay_dir
        else output_path.parent / "calibration-overlays"
    )
    try:
        measurements = json.loads(measurements_path.read_text(encoding="utf-8"))
        renders = render_map(Path(args.renders))
        measurement_pages = measurements.get("pages", [])
        if args.verbose and len(renders) < len(measurement_pages):
            print(
                f"warning: {len(renders)} render page(s) for {len(measurement_pages)} "
                "measurement page(s); missing pages will be reported as errors.",
                file=sys.stderr,
            )
        pages = []
        errors = []
        for page in measurement_pages:
            number = int(page["page"])
            render_path = renders.get(number)
            if render_path is None:
                errors.append({"page": number, "error": "render page is missing"})
                continue
            coordinate_system = page.get("coordinateSystem", {})
            width = int(coordinate_system.get("width", coordinate_system.get("w", 1280)))
            height = int(coordinate_system.get("height", coordinate_system.get("h", 720)))
            tolerance = args.tolerance_px or max(6.0, max(width, height) * 0.005)
            if args.verbose:
                derivation = (
                    f"explicit --tolerance-px={args.tolerance_px}"
                    if args.tolerance_px
                    else f"max(6.0, max({width}, {height}) * 0.005)"
                )
                print(
                    f"page {number}: tolerancePx={tolerance} ({derivation})",
                    file=sys.stderr,
                )
            pages.append(
                analyze_page(
                    page,
                    render_path,
                    overlay_dir,
                    tolerance,
                    args.search_radius,
                    args.minimum_matches,
                )
            )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    statuses = [page["status"] for page in pages]
    overall = (
        "FAIL"
        if "FAIL" in statuses
        else "INCONCLUSIVE"
        if errors or "INCONCLUSIVE" in statuses or not pages
        else "PASS"
    )
    result = {
        "schemaVersion": "2.0",
        "status": overall,
        "generatedBy": "calibrate_reference_render.py",
        "pages": pages,
        "errors": errors,
    }
    write_json(output_path, result)
    make_stdout_robust()
    print(output_path)
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
