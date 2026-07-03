#!/usr/bin/env python3
"""Measure rendered typography candidates and select the closest valid candidate."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

try:
    from PIL import Image, ImageFilter
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow is required: install it with `python -m pip install Pillow`.") from exc


def percentile(histogram: list[int], ratio: float) -> int:
    cutoff = sum(histogram) * ratio
    running = 0
    for value, count in enumerate(histogram):
        running += count
        if running >= cutoff:
            return value
    return 255


def contiguous_runs(values: list[int], minimum: int) -> list[tuple[int, int]]:
    runs = []
    start = None
    gap = 0
    for index, value in enumerate([*values, 0, 0, 0]):
        active = value >= minimum
        if active:
            if start is None:
                start = index
            gap = 0
        elif start is not None:
            gap += 1
            if gap > 2:
                runs.append((start, index - gap))
                start = None
                gap = 0
    return [run for run in runs if run[1] - run[0] + 1 >= 2]


def analyze_render(path: Path, crop: dict) -> dict:
    with Image.open(path) as source:
        image = source.convert("RGB")
    x = int(crop.get("x", 0))
    y = int(crop.get("y", 0))
    w = int(crop.get("w", 0))
    h = int(crop.get("h", 0))
    if w <= 0 or h <= 0:
        raise ValueError(f"renderCrop must have positive dimensions: {path}")
    if x < 0 or y < 0 or x + w > image.width or y + h > image.height:
        raise ValueError(f"renderCrop is outside the rendered image: {path}")
    region = image.crop((x, y, x + w, y + h)).convert("L").filter(ImageFilter.FIND_EDGES)
    threshold = max(24, percentile(region.histogram(), 0.88))
    pixels = region.load()
    points = [
        (px, py)
        for py in range(1, region.height - 1)
        for px in range(1, region.width - 1)
        if pixels[px, py] >= threshold
    ]
    if not points:
        return {
            "inkBBox": None,
            "lineCount": 0,
            "lineBBoxes": [],
            "lineGapPx": None,
            "baselineProxyPx": [],
            "clippingDetected": False,
            "error": "no rendered ink detected",
        }
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)
    row_counts = [0] * region.height
    for _, py in points:
        row_counts[py] += 1
    runs = contiguous_runs(row_counts, max(2, round(region.width * 0.015)))
    line_boxes = []
    for top, bottom in runs:
        line_points = [(px, py) for px, py in points if top <= py <= bottom]
        if not line_points:
            continue
        left = min(point[0] for point in line_points)
        right = max(point[0] for point in line_points)
        line_boxes.append(
            {"x": left, "y": top, "w": right - left + 1, "h": bottom - top + 1}
        )
    gaps = [
        line_boxes[index + 1]["y"] - (line_boxes[index]["y"] + line_boxes[index]["h"])
        for index in range(len(line_boxes) - 1)
    ]
    clipping = min_x <= 1 or min_y <= 1 or max_x >= w - 2 or max_y >= h - 2
    return {
        "inkBBox": {"x": min_x, "y": min_y, "w": max_x - min_x + 1, "h": max_y - min_y + 1},
        "lineCount": len(line_boxes),
        "lineBBoxes": line_boxes,
        "lineGapPx": round(sum(gaps) / len(gaps), 3) if gaps else None,
        "baselineProxyPx": [item["y"] + item["h"] - 1 for item in line_boxes],
        "clippingDetected": clipping,
    }


def relative_error(actual: float | None, expected: float | None, scale: float) -> float:
    if actual is None or expected is None:
        return 0.0
    return abs(float(actual) - float(expected)) / max(1.0, scale)


def score_candidate(candidate: dict, reference: dict, base_dir: Path) -> tuple[float, dict]:
    render_path = Path(candidate.get("renderPath", ""))
    if not render_path.is_absolute():
        render_path = base_dir / render_path
    metrics = analyze_render(render_path, candidate.get("renderCrop", {}))
    expected_bbox = reference.get("glyphBBox") or reference.get("textBlockBBox") or {}
    actual_bbox = metrics.get("inkBBox") or {}
    expected_line_count = int(reference.get("lineCount") or 0)
    actual_line_count = int(metrics.get("lineCount") or 0)
    line_mismatch = expected_line_count > 0 and actual_line_count != expected_line_count
    clipping = bool(metrics.get("clippingDetected"))
    score = 0.0
    score += 0.25 * relative_error(
        actual_bbox.get("w"), expected_bbox.get("w"), expected_bbox.get("w", 1)
    )
    score += 0.30 * relative_error(
        actual_bbox.get("h"), expected_bbox.get("h"), expected_bbox.get("h", 1)
    )
    score += 0.20 * relative_error(
        metrics.get("lineGapPx"), reference.get("lineGapPx"), reference.get("lineGapPx") or 10
    )
    score += 1.0 if line_mismatch else 0.0
    score += 2.0 if clipping else 0.0
    valid = not line_mismatch and not clipping and actual_line_count > 0
    metrics.update(
        {
            "renderPath": str(render_path),
            "lineCountMatches": not line_mismatch,
            "score": round(score, 6),
            "status": "valid" if valid else "rejected",
        }
    )
    return score if valid else math.inf, metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="typography-calibration JSON")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
        data["schemaVersion"] = "2.0"
        failures = []
        for item in data.get("items", []):
            ranked = []
            for index, candidate in enumerate(item.get("candidates", []), start=1):
                candidate.setdefault("id", f"{item.get('id', 'text')}-candidate-{index:02d}")
                try:
                    score, metrics = score_candidate(
                        candidate, item.get("reference", {}), input_path.parent
                    )
                except (OSError, ValueError) as exc:
                    score = math.inf
                    metrics = {"status": "rejected", "error": str(exc)}
                candidate["renderMetrics"] = metrics
                ranked.append((score, candidate))
            valid = [entry for entry in ranked if math.isfinite(entry[0])]
            if not valid:
                failures.append({"itemId": item.get("id"), "error": "no valid rendered candidate"})
                item["selected"] = {"candidateId": None, "needsHumanReview": True}
                continue
            score, selected = min(valid, key=lambda entry: entry[0])
            item["selected"] = {
                "candidateId": selected["id"],
                "fontFamily": selected.get("fontFamily"),
                "fontSizePt": selected.get("fontSizePt"),
                "constructionFontSize": selected.get("constructionFontSize"),
                "fontWeight": selected.get("fontWeight"),
                "lineSpacingPercent": selected.get("lineSpacingPercent"),
                "textBox": selected.get("textBox"),
                "paddingPx": selected.get("paddingPx"),
                "score": round(score, 6),
                "rationale": (
                    "lowest measured render error among non-clipping candidates "
                    "with matching line count"
                ),
                "needsHumanReview": False,
            }
        data["generatedBy"] = "score_typography_candidates.py"
        data["status"] = "PASS" if not failures else "FAIL"
        data["failures"] = failures
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output_path)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
