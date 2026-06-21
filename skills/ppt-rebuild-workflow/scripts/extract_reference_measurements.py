#!/usr/bin/env python3
"""Extract first-pass visual measurement candidates from slide reference images."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def natural_key(path: Path) -> list[object]:
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", path.name)
    ]


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


def percentile_from_histogram(histogram: list[int], percentile: float) -> int:
    total = sum(histogram)
    if total <= 0:
        return 0
    cutoff = total * percentile
    running = 0
    for value, count in enumerate(histogram):
        running += count
        if running >= cutoff:
            return value
    return len(histogram) - 1


def bbox_dict(min_x: int, min_y: int, max_x: int, max_y: int) -> dict[str, int]:
    return {
        "x": int(min_x),
        "y": int(min_y),
        "w": int(max_x - min_x + 1),
        "h": int(max_y - min_y + 1),
    }


def connected_components(
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


def edge_mask(image: Image.Image) -> tuple[bytearray, int]:
    gray = image.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    threshold = max(24, percentile_from_histogram(edges.histogram(), 0.90))
    raw = edges.tobytes()
    return bytearray(1 if value >= threshold else 0 for value in raw), threshold


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
    if axis == "horizontal":
        threshold = max(36, int(width * 0.16))
        counts = [
            sum(mask[y * width : (y + 1) * width])
            for y in range(height)
        ]
        limit = height
    else:
        threshold = max(24, int(height * 0.16))
        counts = [
            sum(mask[y * width + x] for y in range(height))
            for x in range(width)
        ]
        limit = width

    start = None
    for pos in range(limit + 1):
        active = pos < limit and counts[pos] >= threshold
        if active and start is None:
            start = pos
        if (not active or pos == limit) and start is not None:
            end = pos - 1
            if axis == "horizontal":
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

    return sorted(
        regions,
        key=lambda item: item["bbox"]["w"] * item["bbox"]["h"],
        reverse=True,
    )[:max_candidates]


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
        candidates.append(
            {
                "kind": "line",
                "bbox": bbox,
                "confidence": item["confidence"],
                "sourceCandidateIds": [item["id"]],
                "area": bbox["w"] * bbox["h"],
            }
        )

    for item in sorted(candidates, key=lambda value: (value["confidence"], value["area"]), reverse=True):
        if len(anchors) >= max(1, limit):
            break
        if any(bbox_iou(item["bbox"], anchor["bbox"]) >= 0.82 for anchor in anchors):
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
    font = ImageFont.load_default()

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


def analyze_image(
    path: Path,
    page_number: int,
    annotated_dir: Path,
    target_width: int,
    target_height: int,
    min_component_area: int,
    max_candidates: int,
    auto_anchor_limit: int,
) -> dict:
    with Image.open(path) as source:
        original = source.convert("RGB")
        original_size = original.size
        image = original.resize((target_width, target_height), Image.Resampling.LANCZOS)

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

    annotated_path = annotated_dir / f"{path.stem}-measurements.png"
    draw_candidates(image, text_lines, horizontal, vertical, regions, anchors, annotated_path)

    return {
        "page": page_number,
        "image": str(path),
        "originalSize": {"w": original_size[0], "h": original_size[1]},
        "coordinateSystem": {"w": target_width, "h": target_height},
        "scale": {
            "x": round(target_width / original_size[0], 6),
            "y": round(target_height / original_size[1], 6),
        },
        "coordinateTransform": {
            "sourcePxToCanvas": {
                "scaleX": round(target_width / original_size[0], 6),
                "scaleY": round(target_height / original_size[1], 6),
                "offsetX": 0,
                "offsetY": 0,
            },
            "canvasToSourcePx": {
                "scaleX": round(original_size[0] / target_width, 6),
                "scaleY": round(original_size[1] / target_height, 6),
                "offsetX": 0,
                "offsetY": 0,
            },
            "fitMode": "stretch-to-canvas",
        },
        "edgeThreshold": threshold,
        "dominantColors": dominant_colors(image),
        "textLineCandidates": text_lines,
        "horizontalLineCandidates": horizontal,
        "verticalLineCandidates": vertical,
        "regionCandidates": regions,
        "autoAnchors": anchors,
        "annotatedImage": str(annotated_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extract first-pass visual measurement candidates from slide "
            "reference images. Results must be reviewed before PPT construction."
        )
    )
    parser.add_argument("input", help="Reference image file or directory")
    parser.add_argument("--output", required=True, help="JSON output path")
    parser.add_argument("--annotated-dir", help="Directory for annotated images")
    parser.add_argument("--target-width", type=int, default=1280)
    parser.add_argument("--target-height", type=int, default=720)
    parser.add_argument("--min-component-area", type=int, default=8)
    parser.add_argument("--max-candidates", type=int, default=40)
    parser.add_argument("--auto-anchor-limit", type=int, default=12)
    args = parser.parse_args()

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

    pages = [
        analyze_image(
            path,
            page_number=index,
            annotated_dir=annotated_dir,
            target_width=args.target_width,
            target_height=args.target_height,
            min_component_area=args.min_component_area,
            max_candidates=args.max_candidates,
            auto_anchor_limit=args.auto_anchor_limit,
        )
        for index, path in enumerate(files, start=1)
    ]

    result = {
        "settings": {
            "targetWidth": args.target_width,
            "targetHeight": args.target_height,
            "minComponentArea": args.min_component_area,
            "maxCandidates": args.max_candidates,
            "autoAnchorLimit": args.auto_anchor_limit,
            "note": "Candidates and auto anchors are measurement aids. Validate them with a rendered calibration overlay before writing visual-extraction.",
        },
        "pages": pages,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
