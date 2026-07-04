#!/usr/bin/env python3
"""Extract first-pass visual measurement candidates from slide reference images."""

from __future__ import annotations

import argparse
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageStat, UnidentifiedImageError
except ImportError as exc:  # pragma: no cover - exercised only without Pillow
    raise SystemExit("Pillow is required: install it with `python -m pip install Pillow`.") from exc

# Per-image failures we tolerate (bad/corrupt/oversized inputs); anything else
# (e.g. a KeyError from a refactor) must propagate instead of being masked (P2-3).
IMAGE_FAILURE_ERRORS = (OSError, ValueError, UnidentifiedImageError)

try:  # Optional fast path.
    import numpy as np
except ImportError:  # pragma: no cover - environment dependent
    np = None

try:  # Optional connected-component fast path.
    from scipy import ndimage as scipy_ndimage
except ImportError:  # pragma: no cover - environment dependent
    scipy_ndimage = None

try:  # Optional contour/rectangle detector.
    import cv2
except ImportError:  # pragma: no cover - environment dependent
    cv2 = None

from _image_common import (
    IMAGE_EXTENSIONS,
    edge_binary,
    load_image_rgb,
    load_overlay_font,
    natural_key,
)
from _io_common import make_stdout_robust, write_json


def measurement_engine() -> str:
    forced = os.environ.get("PPT_REBUILD_MEASUREMENT_ENGINE", "").strip().lower()
    if forced == "python":
        return "python"
    if forced == "numpy-scipy" and np is not None and scipy_ndimage is not None:
        return "numpy-scipy"
    if cv2 is not None and np is not None:
        return "opencv-numpy"
    if np is not None and scipy_ndimage is not None:
        return "numpy-scipy"
    return "python"


def image_files(path: Path) -> list[Path]:
    if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
        return [path]
    if path.is_dir():
        return sorted(
            [
                item
                for item in path.iterdir()
                if item.suffix.lower() in IMAGE_EXTENSIONS
                and not item.name.startswith("_")
            ],
            key=natural_key,
        )
    return []


def bbox_dict(min_x: int, min_y: int, max_x: int, max_y: int) -> dict[str, int]:
    return {
        "x": int(min_x),
        "y": int(min_y),
        "w": int(max_x - min_x + 1),
        "h": int(max_y - min_y + 1),
    }


def connected_components_python(
    mask: bytearray,
    width: int,
    height: int,
    min_area: int,
) -> list[dict]:
    visited = bytearray(width * height)
    components: list[dict] = []

    for start, enabled in enumerate(mask):
        if not enabled or visited[start]:
            continue
        stack = [start]
        visited[start] = 1
        count = 0
        min_x = width
        min_y = height
        max_x = 0
        max_y = 0

        while stack:
            idx = stack.pop()
            y, x = divmod(idx, width)
            count += 1
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)

            if x > 0:
                neighbor = idx - 1
                if mask[neighbor] and not visited[neighbor]:
                    visited[neighbor] = 1
                    stack.append(neighbor)
            if x < width - 1:
                neighbor = idx + 1
                if mask[neighbor] and not visited[neighbor]:
                    visited[neighbor] = 1
                    stack.append(neighbor)
            if y > 0:
                neighbor = idx - width
                if mask[neighbor] and not visited[neighbor]:
                    visited[neighbor] = 1
                    stack.append(neighbor)
            if y < height - 1:
                neighbor = idx + width
                if mask[neighbor] and not visited[neighbor]:
                    visited[neighbor] = 1
                    stack.append(neighbor)

        if count < min_area:
            continue
        bbox = bbox_dict(min_x, min_y, max_x, max_y)
        bbox_area = max(1, bbox["w"] * bbox["h"])
        components.append(
            {
                "bbox": bbox,
                "edgePixels": count,
                "bboxArea": bbox_area,
                "edgeDensity": round(count / bbox_area, 4),
            }
        )

    return components


def connected_components(
    mask: bytearray,
    width: int,
    height: int,
    min_area: int,
) -> list[dict]:
    if measurement_engine() == "python" or np is None or scipy_ndimage is None:
        return connected_components_python(mask, width, height, min_area)
    array = np.frombuffer(mask, dtype=np.uint8).reshape((height, width)).astype(bool)
    labels, _count = scipy_ndimage.label(array)
    objects = scipy_ndimage.find_objects(labels)
    components = []
    for label_id, slices in enumerate(objects, start=1):
        if slices is None:
            continue
        y_slice, x_slice = slices
        pixels = int(np.count_nonzero(labels[slices] == label_id))
        if pixels < min_area:
            continue
        bbox = {
            "x": int(x_slice.start),
            "y": int(y_slice.start),
            "w": int(x_slice.stop - x_slice.start),
            "h": int(y_slice.stop - y_slice.start),
        }
        area = max(1, bbox["w"] * bbox["h"])
        components.append(
            {
                "bbox": bbox,
                "edgePixels": pixels,
                "bboxArea": area,
                "edgeDensity": round(pixels / area, 4),
            }
        )
    return components


def edge_mask(image: Image.Image) -> tuple[bytearray, int]:
    return edge_binary(image, use_numpy=measurement_engine() != "python")


def dominant_colors(image: Image.Image, count: int = 8) -> list[dict]:
    rgb = image.convert("RGB")
    try:
        quantized = rgb.quantize(colors=count, method=Image.Quantize.MEDIANCUT)
    except AttributeError:
        quantized = rgb.convert("P", palette=Image.ADAPTIVE, colors=count)
    palette = quantized.getpalette() or []
    colors = quantized.getcolors(rgb.width * rgb.height) or []
    result = []
    total = rgb.width * rgb.height
    for pixels, index in sorted(colors, reverse=True):
        offset = index * 3
        color = tuple(palette[offset : offset + 3])
        if len(color) != 3:
            continue
        result.append(
            {
                "hex": "#{:02X}{:02X}{:02X}".format(*color),
                "rgb": list(color),
                "coverage": round(pixels / total, 4),
            }
        )
    return result[:count]


def average_color(image: Image.Image, bbox: dict[str, int]) -> str:
    crop = image.crop(
        (
            bbox["x"],
            bbox["y"],
            bbox["x"] + bbox["w"],
            bbox["y"] + bbox["h"],
        )
    )
    mean = ImageStat.Stat(crop.convert("RGB")).mean
    return "#{:02X}{:02X}{:02X}".format(*(round(value) for value in mean))


def text_line_candidates(
    components: list[dict],
    width: int,
    height: int,
    max_candidates: int,
) -> list[dict]:
    eligible = []
    for component in components:
        bbox = component["bbox"]
        if bbox["h"] < 4 or bbox["h"] > 90:
            continue
        if bbox["w"] > width * 0.75 and bbox["h"] < 10:
            continue
        if bbox["w"] > width * 0.9 or bbox["h"] > height * 0.35:
            continue
        eligible.append(component)

    groups: list[dict] = []
    for component in sorted(
        eligible,
        key=lambda item: (
            item["bbox"]["y"] + item["bbox"]["h"] / 2,
            item["bbox"]["x"],
        ),
    ):
        bbox = component["bbox"]
        center_y = bbox["y"] + bbox["h"] / 2
        placed = False
        for group in groups:
            tolerance = max(5, min(18, group["avgHeight"] * 0.75))
            if abs(center_y - group["centerY"]) <= tolerance:
                group["items"].append(component)
                total = len(group["items"])
                group["centerY"] = (group["centerY"] * (total - 1) + center_y) / total
                group["avgHeight"] = (
                    group["avgHeight"] * (total - 1) + bbox["h"]
                ) / total
                placed = True
                break
        if not placed:
            groups.append(
                {
                    "centerY": center_y,
                    "avgHeight": bbox["h"],
                    "items": [component],
                }
            )

    candidates = []
    for index, group in enumerate(groups, start=1):
        boxes = [item["bbox"] for item in group["items"]]
        min_x = min(box["x"] for box in boxes)
        min_y = min(box["y"] for box in boxes)
        max_x = max(box["x"] + box["w"] - 1 for box in boxes)
        max_y = max(box["y"] + box["h"] - 1 for box in boxes)
        bbox = bbox_dict(min_x, min_y, max_x, max_y)
        if bbox["w"] < 18 or bbox["h"] < 4:
            continue
        if len(group["items"]) < 2 and bbox["w"] < 48:
            continue
        candidates.append(
            {
                "id": f"text-line-candidate-{index:02d}",
                "bbox": bbox,
                "componentCount": len(group["items"]),
                "estimatedLineHeightPx": bbox["h"],
                "confidence": round(
                    min(0.85, 0.25 + math.log2(len(group["items"]) + 1) / 5),
                    2,
                ),
            }
        )

    return sorted(
        candidates,
        key=lambda item: (item["bbox"]["y"], item["bbox"]["x"]),
    )[:max_candidates]


def line_candidates(
    mask: bytearray,
    width: int,
    height: int,
    max_candidates: int,
    axis: str,
) -> list[dict]:
    candidates = []
    array = (
        np.frombuffer(mask, dtype=np.uint8).reshape((height, width))
        if measurement_engine() != "python" and np is not None
        else None
    )
    if axis == "horizontal":
        threshold = max(36, int(width * 0.16))
        counts = (
            array.sum(axis=1).astype(int).tolist()
            if array is not None
            else [sum(mask[y * width : (y + 1) * width]) for y in range(height)]
        )
        limit = height
    else:
        threshold = max(24, int(height * 0.16))
        counts = (
            array.sum(axis=0).astype(int).tolist()
            if array is not None
            else [sum(mask[y * width + x] for y in range(height)) for x in range(width)]
        )
        limit = width

    start = None
    for pos in range(limit + 1):
        active = pos < limit and counts[pos] >= threshold
        if active and start is None:
            start = pos
        if (not active or pos == limit) and start is not None:
            end = pos - 1
            if axis == "horizontal":
                if array is not None:
                    xs = np.nonzero(array[start : end + 1, :])[1].tolist()
                else:
                    xs = []
                    for y in range(start, end + 1):
                        row = mask[y * width : (y + 1) * width]
                        xs.extend(x for x, value in enumerate(row) if value)
                if xs:
                    bbox = bbox_dict(min(xs), start, max(xs), end)
                else:
                    bbox = bbox_dict(0, start, width - 1, end)
                keep = bbox["w"] >= 40 and bbox["h"] <= 12
            else:
                if array is not None:
                    ys = np.nonzero(array[:, start : end + 1])[0].tolist()
                else:
                    ys = []
                    for x in range(start, end + 1):
                        ys.extend(y for y in range(height) if mask[y * width + x])
                if ys:
                    bbox = bbox_dict(start, min(ys), end, max(ys))
                else:
                    bbox = bbox_dict(start, 0, end, height - 1)
                keep = bbox["h"] >= 40 and bbox["w"] <= 12

            if keep:
                candidates.append(
                    {
                        "id": f"{axis}-line-candidate-{len(candidates)+1:02d}",
                        "bbox": bbox,
                        "edgePixelCount": int(sum(counts[start : end + 1])),
                        "confidence": 0.6,
                    }
                )
            start = None

    return candidates[:max_candidates]


def contour_region_candidates(
    image: Image.Image,
    max_candidates: int,
) -> list[dict]:
    if measurement_engine() != "opencv-numpy" or cv2 is None or np is None:
        return []
    rgb = np.asarray(image.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 40, 120)
    edges = cv2.morphologyEx(
        edges,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)),
        iterations=2,
    )
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    width, height = image.size
    canvas_area = width * height
    regions = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < canvas_area * 0.012 or area > canvas_area * 0.94:
            continue
        if w < width * 0.10 or h < height * 0.035:
            continue
        contour_area = max(1.0, float(cv2.contourArea(contour)))
        rectangularity = min(1.0, contour_area / max(1, area))
        if rectangularity < 0.18:
            continue
        bbox = {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}
        perimeter = cv2.arcLength(contour, True)
        polygon = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        regions.append(
            {
                "id": f"contour-region-{len(regions)+1:02d}",
                "bbox": bbox,
                "edgePixels": int(perimeter),
                "edgeDensity": round(perimeter / max(1, area), 4),
                "rectangularity": round(rectangularity, 3),
                "geometry": "rect-like" if 4 <= len(polygon) <= 8 else "region",
                "averageColor": average_color(image, bbox),
                "confidence": round(min(0.95, 0.5 + rectangularity * 0.4), 2),
            }
        )
    selected = []
    for item in sorted(
        regions,
        key=lambda value: (value["confidence"], value["bbox"]["w"] * value["bbox"]["h"]),
        reverse=True,
    ):
        if any(bbox_iou(item["bbox"], existing["bbox"]) > 0.88 for existing in selected):
            continue
        selected.append(item)
        if len(selected) >= max_candidates:
            break
    return selected


def region_candidates(
    components: list[dict],
    image: Image.Image,
    max_candidates: int,
) -> list[dict]:
    width, height = image.size
    regions = []
    for component in components:
        bbox = component["bbox"]
        if bbox["w"] < 20 or bbox["h"] < 12:
            continue
        if bbox["w"] * bbox["h"] < 900:
            continue
        if bbox["w"] > width * 0.96 and bbox["h"] > height * 0.96:
            continue
        if min(bbox["w"], bbox["h"]) <= 8:
            continue
        regions.append(
            {
                "id": f"region-candidate-{len(regions)+1:02d}",
                "bbox": bbox,
                "edgePixels": component["edgePixels"],
                "edgeDensity": component["edgeDensity"],
                "averageColor": average_color(image, bbox),
                "confidence": round(min(0.8, 0.35 + component["edgeDensity"]), 2),
            }
        )

    component_regions = sorted(
        regions,
        key=lambda item: item["bbox"]["w"] * item["bbox"]["h"],
        reverse=True,
    )
    merged = contour_region_candidates(image, max_candidates) + component_regions
    selected = []
    for item in merged:
        if any(bbox_iou(item["bbox"], existing["bbox"]) > 0.9 for existing in selected):
            continue
        selected.append(item)
        if len(selected) >= max_candidates:
            break
    return selected


def bbox_iou(first: dict[str, int], second: dict[str, int]) -> float:
    left = max(first["x"], second["x"])
    top = max(first["y"], second["y"])
    right = min(first["x"] + first["w"], second["x"] + second["w"])
    bottom = min(first["y"] + first["h"], second["y"] + second["h"])
    if right <= left or bottom <= top:
        return 0.0
    intersection = (right - left) * (bottom - top)
    union = first["w"] * first["h"] + second["w"] * second["h"] - intersection
    return intersection / max(1, union)


def auto_anchors(
    regions: list[dict],
    horizontal_lines: list[dict],
    vertical_lines: list[dict],
    width: int,
    height: int,
    limit: int,
) -> list[dict]:
    """Select a compact, role-neutral set of calibration anchors.

    These anchors are not semantic shape decisions. They give the build agent a
    stable coordinate-lock and a small visual overlay to verify after render.
    """
    anchors = [
        {
            "id": "anchor-canvas-frame",
            "kind": "canvas-frame",
            "bbox": {"x": 0, "y": 0, "w": width, "h": height},
            "confidence": 1.0,
            "sourceCandidateIds": [],
            "validation": "render-calibration-overlay",
        }
    ]
    candidates = []
    for item in regions:
        bbox = item["bbox"]
        area_ratio = bbox["w"] * bbox["h"] / max(1, width * height)
        if area_ratio < 0.012 or bbox["w"] < width * 0.10 or bbox["h"] < height * 0.035:
            continue
        candidates.append(
            {
                "kind": "region",
                "bbox": bbox,
                "confidence": item["confidence"],
                "sourceCandidateIds": [item["id"]],
                "area": bbox["w"] * bbox["h"],
            }
        )
    for item in horizontal_lines + vertical_lines:
        bbox = item["bbox"]
        is_horizontal = bbox["w"] >= bbox["h"]
        length_ratio = bbox["w"] / width if is_horizontal else bbox["h"] / height
        if length_ratio < 0.25 or length_ratio > 0.95:
            continue
        candidates.append(
            {
                "kind": "line",
                "bbox": bbox,
                "confidence": item["confidence"],
                "sourceCandidateIds": [item["id"]],
                "area": bbox["w"] * bbox["h"],
            }
        )

    for item in sorted(
        candidates,
        key=lambda value: (value["confidence"], math.sqrt(value["area"])),
        reverse=True,
    ):
        if len(anchors) >= max(1, limit):
            break
        if any(bbox_iou(item["bbox"], anchor["bbox"]) >= 0.75 for anchor in anchors):
            continue
        anchors.append(
            {
                "id": f"anchor-{len(anchors):02d}",
                "kind": item["kind"],
                "bbox": item["bbox"],
                "confidence": item["confidence"],
                "sourceCandidateIds": item["sourceCandidateIds"],
                "validation": "render-calibration-overlay",
            }
        )
    return anchors


def draw_candidates(
    image: Image.Image,
    text_lines: list[dict],
    horizontal_lines: list[dict],
    vertical_lines: list[dict],
    regions: list[dict],
    anchors: list[dict],
    output_path: Path,
) -> None:
    canvas = image.convert("RGB")
    draw = ImageDraw.Draw(canvas, "RGBA")
    font = load_overlay_font()

    def rectangle(item: dict, color: tuple[int, int, int, int], label: str) -> None:
        bbox = item["bbox"]
        xy = [
            bbox["x"],
            bbox["y"],
            bbox["x"] + bbox["w"],
            bbox["y"] + bbox["h"],
        ]
        draw.rectangle(xy, outline=color, width=2)
        draw.text((bbox["x"] + 2, max(0, bbox["y"] - 11)), label, fill=color, font=font)

    for item in regions:
        rectangle(item, (0, 170, 255, 220), item["id"].replace("candidate-", ""))
    for item in horizontal_lines:
        rectangle(item, (255, 210, 0, 230), "h-line")
    for item in vertical_lines:
        rectangle(item, (80, 220, 100, 230), "v-line")
    for item in text_lines:
        rectangle(item, (255, 70, 70, 230), item["id"].replace("candidate-", ""))
    for item in anchors:
        rectangle(item, (0, 240, 150, 230), item["id"].replace("anchor-", "a-"))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)


def fit_reference_image(
    original: Image.Image,
    target_width: int,
    target_height: int,
    requested_mode: str,
) -> tuple[Image.Image, dict, list[str]]:
    source_width, source_height = original.size
    if min(source_width, source_height, target_width, target_height) <= 0:
        raise ValueError("source and target dimensions must be positive")
    source_ratio = source_width / source_height
    target_ratio = target_width / target_height
    ratio_delta = abs(source_ratio / target_ratio - 1.0)
    warnings = []
    mode = requested_mode
    if mode == "auto":
        mode = "contain"
        if ratio_delta > 0.005:
            warnings.append(
                f"aspect ratio differs by {ratio_delta:.2%}; "
                "auto selected contain instead of stretch"
            )

    if mode == "stretch":
        scale_x = target_width / source_width
        scale_y = target_height / source_height
        offset_x = offset_y = 0.0
        canvas = original.resize((target_width, target_height), Image.Resampling.LANCZOS)
    else:
        scale = (
            min(target_width / source_width, target_height / source_height)
            if mode == "contain"
            else max(target_width / source_width, target_height / source_height)
        )
        scale_x = scale_y = scale
        fitted_width = max(1, round(source_width * scale))
        fitted_height = max(1, round(source_height * scale))
        offset_x = (target_width - fitted_width) / 2
        offset_y = (target_height - fitted_height) / 2
        resized = original.resize((fitted_width, fitted_height), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (target_width, target_height), "white")
        canvas.paste(resized, (round(offset_x), round(offset_y)))

    inverse_offset_x = -offset_x / scale_x
    inverse_offset_y = -offset_y / scale_y
    transform = {
        "sourcePxToCanvas": {
            "scaleX": round(scale_x, 6),
            "scaleY": round(scale_y, 6),
            "offsetX": round(offset_x, 3),
            "offsetY": round(offset_y, 3),
        },
        "canvasToSourcePx": {
            "scaleX": round(1 / scale_x, 6),
            "scaleY": round(1 / scale_y, 6),
            "offsetX": round(inverse_offset_x, 3),
            "offsetY": round(inverse_offset_y, 3),
        },
        "fitMode": mode,
        "requestedFitMode": requested_mode,
        "aspectRatioDelta": round(ratio_delta, 6),
    }
    return canvas, transform, warnings


def analyze_image(
    path: Path,
    page_number: int,
    annotated_dir: Path,
    target_width: int,
    target_height: int,
    min_component_area: int,
    max_candidates: int,
    auto_anchor_limit: int,
    fit_mode: str,
) -> dict:
    original = load_image_rgb(path)
    original_size = original.size
    image, transform, warnings = fit_reference_image(
        original,
        target_width,
        target_height,
        fit_mode,
    )

    mask, threshold = edge_mask(image)
    components = connected_components(mask, target_width, target_height, min_component_area)
    text_lines = text_line_candidates(
        components,
        target_width,
        target_height,
        max_candidates,
    )
    horizontal = line_candidates(
        mask,
        target_width,
        target_height,
        max_candidates,
        "horizontal",
    )
    vertical = line_candidates(
        mask,
        target_width,
        target_height,
        max_candidates,
        "vertical",
    )
    regions = region_candidates(components, image, max_candidates)
    anchors = auto_anchors(
        regions,
        horizontal,
        vertical,
        target_width,
        target_height,
        auto_anchor_limit,
    )
    stable_anchor_count = max(0, len(anchors) - 1)
    anchor_status = "PASS" if stable_anchor_count >= 3 else "INSUFFICIENT"

    annotated_path = annotated_dir / f"{path.stem}-measurements.png"
    draw_candidates(image, text_lines, horizontal, vertical, regions, anchors, annotated_path)
    anchor_annotated_path = annotated_dir / f"{path.stem}-anchors.png"
    draw_candidates(image, [], [], [], [], anchors, anchor_annotated_path)

    return {
        "page": page_number,
        "image": str(path),
        "originalSize": {"w": original_size[0], "h": original_size[1]},
        "coordinateSystem": {"width": target_width, "height": target_height},
        "scale": {
            "x": transform["sourcePxToCanvas"]["scaleX"],
            "y": transform["sourcePxToCanvas"]["scaleY"],
        },
        "coordinateTransform": transform,
        "measurementEngine": measurement_engine(),
        "warnings": warnings,
        "edgeThreshold": threshold,
        "dominantColors": dominant_colors(image),
        "textLineCandidates": text_lines,
        "horizontalLineCandidates": horizontal,
        "verticalLineCandidates": vertical,
        "regionCandidates": regions,
        "autoAnchors": anchors,
        "anchorQuality": {
            "status": anchor_status,
            "stableAnchorCount": stable_anchor_count,
            "minimumStableAnchors": 3,
            "message": (
                "stable macro anchors are available"
                if anchor_status == "PASS"
                else "not enough stable macro anchors; do not mark coordinate calibration PASS"
            ),
        },
        "annotatedImage": str(annotated_path),
        "anchorAnnotatedImage": str(anchor_annotated_path),
    }


def print_engine_doctor() -> None:
    """Report the selected measurement engine and dependency availability (P3-2)."""
    engine = measurement_engine()
    forced = os.environ.get("PPT_REBUILD_MEASUREMENT_ENGINE", "").strip() or "(unset)"
    print(f"measurement engine: {engine}")
    print(f"  PPT_REBUILD_MEASUREMENT_ENGINE={forced}")
    print(f"  numpy:          {'available' if np is not None else 'MISSING'}")
    print(f"  scipy.ndimage:  {'available' if scipy_ndimage is not None else 'MISSING'}")
    print(f"  opencv (cv2):   {'available' if cv2 is not None else 'MISSING'}")
    if engine == "python":
        print(
            "WARNING: pure-Python fallback — connected components and edge binarization "
            "run without numpy; large batches will be slow."
        )
        print("  Install the [fast] extra (numpy/scipy/opencv) for the accelerated path.")
    else:
        print("OK: accelerated engine selected.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extract first-pass visual measurement candidates from slide "
            "reference images. Results must be reviewed before PPT construction."
        )
    )
    parser.add_argument("input", nargs="?", help="Reference image file or directory")
    parser.add_argument("--output", help="JSON output path")
    parser.add_argument("--annotated-dir", help="Directory for annotated images")
    parser.add_argument("--target-width", type=int, default=1280)
    parser.add_argument("--target-height", type=int, default=720)
    parser.add_argument(
        "--fit-mode",
        choices=("auto", "contain", "cover", "stretch"),
        default="auto",
    )
    parser.add_argument("--min-component-area", type=int, default=8)
    parser.add_argument("--max-candidates", type=int, default=40)
    parser.add_argument("--auto-anchor-limit", type=int, default=12)
    parser.add_argument(
        "--jobs",
        type=int,
        default=0,
        help=(
            "Worker processes for per-page analysis; 0 (default) uses "
            "min(cpu_count, page_count). Use 1 to force serial (debugging)."
        ),
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Print measurement-engine and dependency diagnosis, then exit.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-page progress to stderr (stdout still prints only the output path).",
    )
    args = parser.parse_args()

    if args.doctor:
        print_engine_doctor()
        return 0
    if not args.input:
        parser.error("input is required")
    if not args.output:
        parser.error("--output is required")

    if args.target_width <= 0 or args.target_height <= 0:
        parser.error("--target-width and --target-height must be positive")
    if args.min_component_area <= 0 or args.max_candidates <= 0:
        parser.error("candidate limits must be positive")
    if args.auto_anchor_limit < 1:
        parser.error("--auto-anchor-limit must be at least 1")

    input_path = Path(args.input)
    files = image_files(input_path)
    if not files:
        raise SystemExit(f"No reference images found: {input_path}")

    output_path = Path(args.output)
    annotated_dir = (
        Path(args.annotated_dir)
        if args.annotated_dir
        else output_path.with_suffix("").parent / f"{output_path.stem}-annotated"
    )
    annotated_dir.mkdir(parents=True, exist_ok=True)

    analyze_kwargs = dict(
        annotated_dir=annotated_dir,
        target_width=args.target_width,
        target_height=args.target_height,
        min_component_area=args.min_component_area,
        max_candidates=args.max_candidates,
        auto_anchor_limit=args.auto_anchor_limit,
        fit_mode=args.fit_mode,
    )
    worker_count = args.jobs if args.jobs > 0 else (os.cpu_count() or 1)
    worker_count = max(1, min(worker_count, len(files)))

    indexed_files = list(enumerate(files, start=1))
    results_by_index: dict[int, dict] = {}
    failed_pages = []

    def record_failure(index: int, path: Path, exc: BaseException) -> None:
        failed_pages.append({"page": index, "image": str(path), "error": str(exc)})
        print(f"warning: failed to analyze {path}: {exc}", file=sys.stderr)

    total = len(indexed_files)
    if worker_count == 1:
        for index, path in indexed_files:
            if args.verbose:
                print(f"page {index}/{total} ({path.name})", file=sys.stderr)
            try:
                results_by_index[index] = analyze_image(
                    path, page_number=index, **analyze_kwargs
                )
            except IMAGE_FAILURE_ERRORS as exc:  # Continue the batch; report the failed image.
                record_failure(index, path, exc)
    else:
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            future_to_item = {
                executor.submit(analyze_image, path, page_number=index, **analyze_kwargs): (
                    index,
                    path,
                )
                for index, path in indexed_files
            }
            completed = 0
            for future in as_completed(future_to_item):
                index, path = future_to_item[future]
                if args.verbose:
                    completed += 1
                    print(f"page {completed}/{total} done ({path.name})", file=sys.stderr)
                try:
                    results_by_index[index] = future.result()
                except IMAGE_FAILURE_ERRORS as exc:  # Continue the batch; report the failed image.
                    record_failure(index, path, exc)

    # Reassemble deterministically by page index so the output is identical to the
    # serial run regardless of worker completion order.
    pages = [results_by_index[index] for index in sorted(results_by_index)]
    failed_pages.sort(key=lambda item: item["page"])

    result = {
        "settings": {
            "schemaVersion": "2.0",
            "targetWidth": args.target_width,
            "targetHeight": args.target_height,
            "minComponentArea": args.min_component_area,
            "maxCandidates": args.max_candidates,
            "autoAnchorLimit": args.auto_anchor_limit,
            "fitMode": args.fit_mode,
            "measurementEngine": measurement_engine(),
            "note": (
                "Candidates and auto anchors are measurement aids. Validate them with a "
                "rendered calibration overlay before writing visual-extraction."
            ),
        },
        "pages": pages,
        "failedPages": failed_pages,
    }
    write_json(output_path, result)
    make_stdout_robust()
    print(output_path)
    return 0 if pages else 2


if __name__ == "__main__":
    raise SystemExit(main())
