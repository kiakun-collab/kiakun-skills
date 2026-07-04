#!/usr/bin/env python3
"""Audit PPTX text frames, inherited placeholders, and thin-shape collisions."""

from __future__ import annotations

import argparse
import json
import math
import posixpath
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

from _io_common import write_json
from _pptx_common import NS, group_transform, shape_name, slide_sort_key

REL_NS = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
SLIDE_LAYOUT_REL = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout"
)
SLIDE_MASTER_REL = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster"
)
DEFAULT_LINE_WIDTH_EMU = 12700


def related_part(
    zf: zipfile.ZipFile,
    source_part: str,
    relationship_type: str,
    names: set[str] | None = None,
    relationship_cache: dict[str, ET.Element] | None = None,
) -> str | None:
    source = PurePosixPath(source_part)
    rels_name = str(source.parent / "_rels" / f"{source.name}.rels")
    names = names if names is not None else set(zf.namelist())
    if rels_name not in names:
        return None
    if relationship_cache is not None and rels_name in relationship_cache:
        root = relationship_cache[rels_name]
    else:
        root = ET.fromstring(zf.read(rels_name))
        if relationship_cache is not None:
            relationship_cache[rels_name] = root
    for relationship in root.findall("./rel:Relationship", REL_NS):
        if relationship.attrib.get("Type") != relationship_type:
            continue
        target = relationship.attrib.get("Target", "")
        return posixpath.normpath(
            posixpath.join(str(source.parent), target)
        ).lstrip("/")
    return None


def raw_frame(shape: ET.Element) -> tuple[dict[str, float], ET.Element] | None:
    xfrm = shape.find("./p:spPr/a:xfrm", NS)
    if xfrm is None:
        return None
    off = xfrm.find("./a:off", NS)
    ext = xfrm.find("./a:ext", NS)
    if off is None or ext is None:
        return None
    return (
        {
            "x": float(off.attrib.get("x", "0")),
            "y": float(off.attrib.get("y", "0")),
            "w": float(ext.attrib.get("cx", "0")),
            "h": float(ext.attrib.get("cy", "0")),
        },
        xfrm,
    )


def apply_transform(
    frame: dict[str, float],
    transform: tuple[float, float, float, float],
) -> dict[str, float]:
    sx, sy, tx, ty = transform
    return {
        "x": frame["x"] * sx + tx,
        "y": frame["y"] * sy + ty,
        "w": frame["w"] * abs(sx),
        "h": frame["h"] * abs(sy),
    }


def rotated_aabb(frame: dict[str, float], rotation_units: int) -> dict[str, float]:
    angle = math.radians(rotation_units / 60000)
    width = abs(frame["w"] * math.cos(angle)) + abs(frame["h"] * math.sin(angle))
    height = abs(frame["w"] * math.sin(angle)) + abs(frame["h"] * math.cos(angle))
    center_x = frame["x"] + frame["w"] / 2
    center_y = frame["y"] + frame["h"] / 2
    return {
        "x": center_x - width / 2,
        "y": center_y - height / 2,
        "w": width,
        "h": height,
    }


def line_width(shape: ET.Element) -> int:
    line = shape.find("./p:spPr/a:ln", NS)
    if line is None:
        return DEFAULT_LINE_WIDTH_EMU
    return int(line.attrib.get("w", str(DEFAULT_LINE_WIDTH_EMU)))


def expand_thin_frame(frame: dict[str, float], minimum: float) -> dict[str, float]:
    result = dict(frame)
    if result["w"] < minimum:
        center = result["x"] + result["w"] / 2
        result["x"] = center - minimum / 2
        result["w"] = minimum
    if result["h"] < minimum:
        center = result["y"] + result["h"] / 2
        result["y"] = center - minimum / 2
        result["h"] = minimum
    return result


def placeholder_key(shape: ET.Element) -> tuple[str, str] | None:
    placeholder = shape.find("./p:nvSpPr/p:nvPr/p:ph", NS)
    if placeholder is None:
        return None
    return (
        placeholder.attrib.get("idx", ""),
        placeholder.attrib.get("type", "body"),
    )


def find_placeholder(root: ET.Element | None, key: tuple[str, str]) -> ET.Element | None:
    if root is None:
        return None
    index, placeholder_type = key
    candidates = root.findall(".//p:sp", NS)
    if index:
        for shape in candidates:
            candidate = placeholder_key(shape)
            if candidate and candidate[0] == index:
                return shape
    for shape in candidates:
        candidate = placeholder_key(shape)
        if candidate and candidate[1] == placeholder_type:
            return shape
    return None


def placeholder_index(root: ET.Element | None) -> dict[str, dict[str, ET.Element]]:
    result = {"idx": {}, "type": {}}
    if root is None:
        return result
    for shape in root.findall(".//p:sp", NS):
        key = placeholder_key(shape)
        if key is None:
            continue
        index, placeholder_type = key
        if index:
            result["idx"].setdefault(index, shape)
        result["type"].setdefault(placeholder_type, shape)
    return result


def inherited_frame(
    shape: ET.Element,
    layout_index: dict[str, dict[str, ET.Element]],
    master_index: dict[str, dict[str, ET.Element]],
) -> tuple[dict[str, float] | None, str]:
    key = placeholder_key(shape)
    if key is None:
        return None, "unresolved"
    index, placeholder_type = key
    layout_shape = layout_index["idx"].get(index) if index else None
    if layout_shape is None:
        layout_shape = layout_index["type"].get(placeholder_type)
    if layout_shape is not None:
        frame = raw_frame(layout_shape)
        if frame is not None:
            return frame[0], "layout"
    master_shape = master_index["idx"].get(index) if index else None
    if master_shape is None:
        master_shape = master_index["type"].get(placeholder_type)
    if master_shape is not None:
        frame = raw_frame(master_shape)
        if frame is not None:
            return frame[0], "master"
    return None, "unresolved"


def overlap(a: dict[str, float], b: dict[str, float]) -> dict[str, float] | None:
    left = max(a["x"], b["x"])
    top = max(a["y"], b["y"])
    right = min(a["x"] + a["w"], b["x"] + b["w"])
    bottom = min(a["y"] + a["h"], b["y"] + b["h"])
    if right <= left or bottom <= top:
        return None
    return {"x": left, "y": top, "w": right - left, "h": bottom - top}


def frame_px(frame: dict[str, float], slide_w: int, slide_h: int) -> dict[str, float]:
    return {
        "x": round(frame["x"] / slide_w * 1280, 2),
        "y": round(frame["y"] / slide_h * 720, 2),
        "w": round(frame["w"] / slide_w * 1280, 2),
        "h": round(frame["h"] / slide_h * 720, 2),
    }


def collect_slide_shapes(
    root: ET.Element,
) -> tuple[list[tuple[ET.Element, tuple[float, float, float, float]]], int, list[str]]:
    collected: list[tuple[ET.Element, tuple[float, float, float, float]]] = []
    resolved_groups = 0
    risks: list[str] = []
    tree = root.find(".//p:spTree", NS)
    if tree is None:
        return collected, resolved_groups, risks

    def visit(container: ET.Element, transform: tuple[float, float, float, float]) -> None:
        nonlocal resolved_groups
        for child in list(container):
            if child.tag in {
                f"{{{NS['p']}}}sp",
                f"{{{NS['p']}}}cxnSp",
            }:
                collected.append((child, transform))
            elif child.tag == f"{{{NS['p']}}}grpSp":
                next_transform, risk = group_transform(child, transform)
                if next_transform is None:
                    risks.append(risk or "group transform unresolved")
                    continue
                resolved_groups += 1
                visit(child, next_transform)

    visit(tree, (1.0, 1.0, 0.0, 0.0))
    return collected, resolved_groups, risks


def audit(pptx_path: Path, body_min_chars: int, min_overlap_px: float) -> dict:
    with zipfile.ZipFile(pptx_path) as zf:
        names = set(zf.namelist())
        if "ppt/presentation.xml" not in names:
            raise ValueError("PPTX package has no ppt/presentation.xml")
        presentation = ET.fromstring(zf.read("ppt/presentation.xml"))
        size = presentation.find("./p:sldSz", NS)
        if size is None:
            raise ValueError("ppt/presentation.xml has no p:sldSz")
        slide_w = int(size.attrib.get("cx", "0"))
        slide_h = int(size.attrib.get("cy", "0"))
        if slide_w <= 0 or slide_h <= 0:
            raise ValueError("ppt/presentation.xml has invalid slide dimensions")
        slide_names = sorted(
            [
                name
                for name in names
                if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
            ],
            key=slide_sort_key,
        )
        pages = []
        total_intersections = 0
        total_thin_intersections = 0
        total_body_candidates = 0
        total_connectors = 0
        total_direct = 0
        total_inherited = 0
        total_unresolved = 0
        total_rotated = 0
        total_groups_resolved = 0
        total_groups_unresolved = 0
        relationship_cache: dict[str, ET.Element] = {}
        part_cache: dict[str, ET.Element] = {}
        placeholder_cache: dict[str, dict[str, dict[str, ET.Element]]] = {}

        for page_number, slide_name in enumerate(slide_names, start=1):
            root = ET.fromstring(zf.read(slide_name))
            layout_name = related_part(
                zf, slide_name, SLIDE_LAYOUT_REL, names, relationship_cache
            )
            if layout_name and layout_name not in part_cache:
                part_cache[layout_name] = ET.fromstring(zf.read(layout_name))
            layout_root = part_cache.get(layout_name) if layout_name else None
            master_name = (
                related_part(
                    zf, layout_name, SLIDE_MASTER_REL, names, relationship_cache
                )
                if layout_name
                else None
            )
            if master_name and master_name not in part_cache:
                part_cache[master_name] = ET.fromstring(zf.read(master_name))
            master_root = part_cache.get(master_name) if master_name else None
            if layout_name and layout_name not in placeholder_cache:
                placeholder_cache[layout_name] = placeholder_index(layout_root)
            if master_name and master_name not in placeholder_cache:
                placeholder_cache[master_name] = placeholder_index(master_root)
            layout_placeholders = placeholder_cache.get(
                layout_name or "", {"idx": {}, "type": {}}
            )
            master_placeholders = placeholder_cache.get(
                master_name or "", {"idx": {}, "type": {}}
            )
            shapes, resolved_groups, group_risks = collect_slide_shapes(root)
            text_shapes = []
            thin_shapes = []
            direct_count = 0
            inherited_count = 0
            unresolved_count = 0
            connector_count = 0
            rotated_count = 0
            geometry_risks = [
                {"kind": "groupTransform", "detail": detail} for detail in group_risks
            ]

            for shape_index, (shape, transform) in enumerate(shapes, start=1):
                is_connector = shape.tag.endswith("cxnSp")
                if is_connector:
                    connector_count += 1
                text = "".join(
                    node.text or "" for node in shape.findall(".//a:t", NS)
                ).strip()
                frame_data = raw_frame(shape)
                source = "direct"
                inherited_from = None
                if frame_data is None and text:
                    inherited, inherited_from = inherited_frame(
                        shape, layout_placeholders, master_placeholders
                    )
                    if inherited is None:
                        unresolved_count += 1
                        geometry_risks.append(
                            {
                                "kind": "unresolvedTextFrame",
                                "shapeName": shape_name(shape),
                            }
                        )
                        continue
                    frame = inherited
                    source = "inherited"
                    inherited_count += 1
                elif frame_data is None:
                    continue
                else:
                    frame, xfrm = frame_data
                    frame = apply_transform(frame, transform)
                    rotation = int(xfrm.attrib.get("rot", "0"))
                    if rotation:
                        frame = rotated_aabb(frame, rotation)
                        rotated_count += 1
                    if text:
                        direct_count += 1

                if text:
                    item = {
                        "shapeIndex": shape_index,
                        "shapeName": shape_name(shape),
                        "text": text,
                        "textLength": len(text),
                        "frameSource": source,
                        "inheritedFrom": inherited_from,
                        "frameEmu": {key: round(value) for key, value in frame.items()},
                        "framePx": frame_px(frame, slide_w, slide_h),
                    }
                    text_shapes.append(item)
                    continue

                minimum = line_width(shape) if is_connector else 1
                collision_frame = expand_thin_frame(frame, minimum)
                pixels = frame_px(collision_frame, slide_w, slide_h)
                long_axis = max(pixels["w"], pixels["h"])
                short_axis = min(pixels["w"], pixels["h"])
                if is_connector or (long_axis >= 20 and short_axis <= 8):
                    thin_shapes.append(
                        {
                            "shapeIndex": shape_index,
                            "shapeName": shape_name(shape),
                            "objectType": "connector" if is_connector else "shape",
                            "frameEmu": {
                                key: round(value) for key, value in collision_frame.items()
                            },
                            "framePx": pixels,
                        }
                    )

            intersections = []
            for index, first in enumerate(text_shapes):
                for second in text_shapes[index + 1 :]:
                    hit = overlap(first["frameEmu"], second["frameEmu"])
                    if hit is None:
                        continue
                    width_px = hit["w"] / slide_w * 1280
                    height_px = hit["h"] / slide_h * 720
                    if width_px < min_overlap_px or height_px < min_overlap_px:
                        continue
                    intersections.append(
                        {
                            "a": first["text"][:80],
                            "b": second["text"][:80],
                            "overlapPx": {
                                "w": round(width_px, 2),
                                "h": round(height_px, 2),
                            },
                        }
                    )

            body_candidates = [
                item for item in text_shapes if item["textLength"] >= body_min_chars
            ]
            thin_intersections = []
            for text_shape in text_shapes:
                for thin_shape in thin_shapes:
                    hit = overlap(text_shape["frameEmu"], thin_shape["frameEmu"])
                    if hit is None:
                        continue
                    width_px = hit["w"] / slide_w * 1280
                    height_px = hit["h"] / slide_h * 720
                    if width_px < min_overlap_px or height_px < min_overlap_px:
                        continue
                    thin_intersections.append(
                        {
                            "text": text_shape["text"][:80],
                            "textShapeName": text_shape["shapeName"],
                            "thinShapeName": thin_shape["shapeName"],
                            "thinShapeType": thin_shape["objectType"],
                            "thinShapeFramePx": thin_shape["framePx"],
                            "overlapPx": {
                                "w": round(width_px, 2),
                                "h": round(height_px, 2),
                            },
                        }
                    )

            page = {
                "page": page_number,
                "textShapeCount": len(text_shapes),
                "directFrameCount": direct_count,
                "inheritedFrameCount": inherited_count,
                "unresolvedTextFrameCount": unresolved_count,
                "connectorCount": connector_count,
                "rotationAdjustedShapeCount": rotated_count,
                "groupTransformResolvedCount": resolved_groups,
                "unresolvedGroupTransformCount": len(group_risks),
                "geometryCoverageRisks": geometry_risks,
                "bodyCandidateCount": len(body_candidates),
                "bodyCandidates": body_candidates,
                "textFrameIntersections": intersections,
                "thinShapeTextFrameIntersections": thin_intersections,
            }
            pages.append(page)
            total_intersections += len(intersections)
            total_thin_intersections += len(thin_intersections)
            total_body_candidates += len(body_candidates)
            total_connectors += connector_count
            total_direct += direct_count
            total_inherited += inherited_count
            total_unresolved += unresolved_count
            total_rotated += rotated_count
            total_groups_resolved += resolved_groups
            total_groups_unresolved += len(group_risks)

        return {
            "pptx": str(pptx_path),
            "settings": {
                "bodyMinChars": body_min_chars,
                "minOverlapPx": min_overlap_px,
                "coordinateSystemPx": {"width": 1280, "height": 720},
            },
            "slideSizeEmu": {"w": slide_w, "h": slide_h},
            "pages": pages,
            "totals": {
                "textFrameIntersections": total_intersections,
                "thinShapeTextFrameIntersections": total_thin_intersections,
                "bodyCandidates": total_body_candidates,
                "connectorCount": total_connectors,
                "directFrameCount": total_direct,
                "inheritedFrameCount": total_inherited,
                "unresolvedTextFrameCount": total_unresolved,
                "rotationAdjustedShapeCount": total_rotated,
                "groupTransformResolvedCount": total_groups_resolved,
                "unresolvedGroupTransformCount": total_groups_unresolved,
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit PPTX text frames, inherited placeholders, connectors, "
            "long-body candidates, and thin-shape collision risks."
        )
    )
    parser.add_argument("pptx", help="Path to PPTX")
    parser.add_argument("--output", required=True, help="JSON output path")
    parser.add_argument("--body-min-chars", type=int, default=45)
    parser.add_argument("--min-overlap-px", type=float, default=1.0)
    args = parser.parse_args()

    pptx_path = Path(args.pptx)
    if not pptx_path.exists():
        print(f"PPTX not found: {pptx_path}", file=sys.stderr)
        return 2
    try:
        result = audit(
            pptx_path,
            body_min_chars=args.body_min_chars,
            min_overlap_px=args.min_overlap_px,
        )
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(f"PPTX text-frame audit failed: {exc}", file=sys.stderr)
        return 2
    write_json(Path(args.output), result)
    print(json.dumps(result["totals"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
