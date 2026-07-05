#!/usr/bin/env python3
"""Audit editable structure, fonts, roles, and full-slide image risks in PPTX."""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from _io_common import write_json
from _pptx_common import NS, group_transform, shape_name, slide_sort_key

ROLE_PREFIXES = (
    ("content-image", ("content-image-", "content_image-", "content-pic-")),
    ("page-number", ("page-number-", "page_number-", "slide-number-")),
    ("body-panel", ("body-panel-", "body_panel-", "panel-")),
    ("body-text", ("body-text-", "body_text-", "body-copy-")),
    ("footer-line", ("footer-line-", "footer_line-", "page-line-")),
    ("decor-line", ("decor-line-", "decor_line-", "divider-", "line-")),
    ("background", ("background-", "background_", "bg-")),
    ("subtitle", ("subtitle-", "subtitle_")),
    ("person", ("person-", "person_", "character-")),
    ("kicker", ("kicker-", "kicker_", "eyebrow-")),
    ("title", ("title-", "title_")),
    ("tag", ("tag-", "tag_", "label-", "label_")),
    ("border", ("border-", "border_", "frame-")),
    ("shade", ("shade-", "shade_", "overlay-", "reading-zone-")),
)

FONT_SLOTS = {
    "latin": "latinFonts",
    "ea": "eastAsianFonts",
    "cs": "complexScriptFonts",
    "sym": "symbolFonts",
}

THEME_TOKEN_MAP = {
    "+mj-lt": ("major", "latin"),
    "+mj-ea": ("major", "ea"),
    "+mj-cs": ("major", "cs"),
    "+mn-lt": ("minor", "latin"),
    "+mn-ea": ("minor", "ea"),
    "+mn-cs": ("minor", "cs"),
}


def read_xml(zf: zipfile.ZipFile, name: str) -> ET.Element:
    return ET.fromstring(zf.read(name))


def shape_role(name: str) -> str:
    lowered = name.strip().lower()
    for role, prefixes in ROLE_PREFIXES:
        if lowered in {role, role.replace("-", "_")}:
            return role
        if lowered.startswith(prefixes):
            return role
    return "unclassified"


def increment(counts: dict[str, int], key: str) -> None:
    counts[key] = counts.get(key, 0) + 1


def frame_of_picture(
    picture: ET.Element,
    transform: tuple[float, float, float, float] = (1.0, 1.0, 0.0, 0.0),
) -> dict[str, int] | None:
    xfrm = picture.find("./p:spPr/a:xfrm", NS)
    if xfrm is None:
        return None
    off = xfrm.find("./a:off", NS)
    ext = xfrm.find("./a:ext", NS)
    if off is None or ext is None:
        return None
    sx, sy, tx, ty = transform
    return {
        "x": round(int(off.attrib.get("x", "0")) * sx + tx),
        "y": round(int(off.attrib.get("y", "0")) * sy + ty),
        "w": round(int(ext.attrib.get("cx", "0")) * sx),
        "h": round(int(ext.attrib.get("cy", "0")) * sy),
    }


def collect_pictures(
    root: ET.Element,
) -> tuple[list[tuple[ET.Element, tuple[float, float, float, float] | None]], list[dict]]:
    pictures = []
    risks = []
    tree = root.find(".//p:spTree", NS)
    if tree is None:
        return pictures, risks

    def visit(container: ET.Element, transform, inherited_risk: str | None = None) -> None:
        for child in list(container):
            if child.tag == f"{{{NS['p']}}}pic":
                pictures.append((child, None if inherited_risk else transform))
                if inherited_risk:
                    risks.append(
                        {
                            "kind": "groupPictureTransform",
                            "pictureName": shape_name(child, "picture"),
                            "detail": inherited_risk,
                        }
                    )
            elif child.tag == f"{{{NS['p']}}}grpSp":
                next_transform, risk = group_transform(child, transform)
                if next_transform is None:
                    visit(child, transform, risk or "group transform unresolved")
                else:
                    visit(child, next_transform, inherited_risk)

    visit(tree, (1.0, 1.0, 0.0, 0.0))
    return pictures, risks


def coverage_ratio(frame: dict[str, int], slide_w: int, slide_h: int) -> float:
    if slide_w <= 0 or slide_h <= 0:
        raise ValueError("slide dimensions must be positive")
    left = max(0, frame["x"])
    top = max(0, frame["y"])
    right = min(slide_w, frame["x"] + frame["w"])
    bottom = min(slide_h, frame["y"] + frame["h"])
    if right <= left or bottom <= top:
        return 0.0
    return (right - left) * (bottom - top) / (slide_w * slide_h)


def relevant_font_parts(names: list[str]) -> list[str]:
    patterns = (
        r"ppt/slides/slide\d+\.xml$",
        r"ppt/slideLayouts/slideLayout\d+\.xml$",
        r"ppt/slideMasters/slideMaster\d+\.xml$",
        r"ppt/theme/theme\d+\.xml$",
    )
    return sorted(name for name in names if any(re.fullmatch(p, name) for p in patterns))


def read_theme_font_map(
    zf: zipfile.ZipFile,
    names: list[str],
    roots: dict[str, ET.Element] | None = None,
) -> tuple[dict, set[str]]:
    mapping: dict[str, dict[str, str]] = {"major": {}, "minor": {}}
    all_theme_fonts: set[str] = set()
    for name in names:
        if not re.fullmatch(r"ppt/theme/theme\d+\.xml", name):
            continue
        root = roots[name] if roots is not None and name in roots else read_xml(zf, name)
        for family, element_name in (("major", "majorFont"), ("minor", "minorFont")):
            node = root.find(f".//a:{element_name}", NS)
            if node is None:
                continue
            for slot in ("latin", "ea", "cs"):
                font = node.find(f"./a:{slot}", NS)
                typeface = font.attrib.get("typeface", "").strip() if font is not None else ""
                if typeface:
                    mapping[family][slot] = typeface
                    all_theme_fonts.add(typeface)
            for supplemental in node.findall("./a:font", NS):
                typeface = supplemental.attrib.get("typeface", "").strip()
                if typeface:
                    all_theme_fonts.add(typeface)
    return mapping, all_theme_fonts


def collect_fonts(
    zf: zipfile.ZipFile,
    names: list[str],
    roots: dict[str, ET.Element] | None = None,
) -> tuple[dict[str, set[str]], set[str], list[dict[str, str]]]:
    font_sets = {field: set() for field in FONT_SLOTS.values()}
    theme_map, theme_fonts = read_theme_font_map(zf, names, roots)
    unresolved: list[dict[str, str]] = []
    parts = relevant_font_parts(names)

    for part_name in parts:
        root = (
            roots[part_name]
            if roots is not None and part_name in roots
            else read_xml(zf, part_name)
        )
        for slot, output_field in FONT_SLOTS.items():
            for node in root.findall(f".//a:{slot}", NS):
                typeface = node.attrib.get("typeface", "").strip()
                if not typeface:
                    if part_name.startswith("ppt/theme/"):
                        unresolved.append(
                            {
                                "part": part_name,
                                "slot": slot,
                                "reason": "theme font slot is empty",
                            }
                        )
                    continue
                if typeface.startswith("+"):
                    theme_key = THEME_TOKEN_MAP.get(typeface)
                    resolved = (
                        theme_map.get(theme_key[0], {}).get(theme_key[1])
                        if theme_key
                        else None
                    )
                    if resolved:
                        font_sets[output_field].add(resolved)
                    else:
                        unresolved.append(
                            {
                                "part": part_name,
                                "slot": slot,
                                "typeface": typeface,
                                "reason": "theme font token could not be resolved",
                            }
                        )
                else:
                    font_sets[output_field].add(typeface)

        if part_name.startswith("ppt/slides/"):
            for shape in root.findall(".//p:sp", NS):
                text = "".join(node.text or "" for node in shape.findall(".//a:t", NS)).strip()
                if not text:
                    continue
                if not any(shape.findall(f".//a:{slot}", NS) for slot in FONT_SLOTS):
                    unresolved.append(
                        {
                            "part": part_name,
                            "shapeName": shape_name(shape, "shape"),
                            "reason": "text has no explicit font slots; inheritance is unresolved",
                        }
                    )
    deduplicated = []
    seen = set()
    for item in unresolved:
        key = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            deduplicated.append(item)
    return font_sets, theme_fonts, deduplicated


def collect_font_sizes(roots, slide_names):
    """收集 slide 内所有字号 sz（1/100 pt）→ (fontSizesPt, nonEvenFontSizesPt)。

    偶数整数 pt ⇔ sz % 200 == 0；奇数 pt 或半号（如 11pt=1100、10.5pt=1050）列入 nonEven。
    对应 image-ppt 的"字号必须偶数整数磅"包内检查（勿用 px 判断偶数）。
    """
    sizes: set[int] = set()
    for name in slide_names:
        root = roots.get(name)
        if root is None:
            continue
        for tag in ("a:rPr", "a:defRPr", "a:endParaRPr"):
            for node in root.findall(f".//{tag}", NS):
                sz = node.attrib.get("sz")
                if sz and sz.isdigit():
                    sizes.add(int(sz))
    font_sizes_pt = sorted(round(s / 100, 2) for s in sizes)
    non_even = sorted(round(s / 100, 2) for s in sizes if s % 200 != 0)
    return font_sizes_pt, non_even


def audit(pptx_path: Path) -> dict:
    with zipfile.ZipFile(pptx_path) as zf:
        names = zf.namelist()
        root_cache = {
            name: read_xml(zf, name)
            for name in relevant_font_parts(names)
        }
        if "ppt/presentation.xml" not in names:
            raise ValueError("PPTX package has no ppt/presentation.xml")
        presentation = read_xml(zf, "ppt/presentation.xml")
        slide_size = presentation.find("./p:sldSz", NS)
        if slide_size is None:
            raise ValueError("ppt/presentation.xml has no p:sldSz")
        slide_w = int(slide_size.attrib.get("cx", "0"))
        slide_h = int(slide_size.attrib.get("cy", "0"))
        if slide_w <= 0 or slide_h <= 0:
            raise ValueError("ppt/presentation.xml has invalid slide dimensions")
        slide_names = sorted(
            [name for name in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)],
            key=slide_sort_key,
        )
        media_names = [
            name for name in names if name.startswith("ppt/media/") and not name.endswith("/")
        ]
        empty_media = [
            name for name in media_names if zf.getinfo(name).file_size == 0
        ]
        font_sets, theme_fonts, unresolved_fonts = collect_fonts(zf, names, root_cache)

        totals = {
            "textRunCount": 0,
            "txBodyCount": 0,
            "shapeCount": 0,
            "pictureCount": 0,
        }
        total_roles: dict[str, int] = {}
        text_roles: dict[str, int] = {}
        non_text_roles: dict[str, int] = {}
        picture_roles: dict[str, int] = {}
        unknown_names: set[str] = set()
        full_slide_risk_pages: list[int] = []
        picture_geometry_risks: list[dict] = []
        pages = []

        for page_number, slide_name in enumerate(slide_names, start=1):
            root = root_cache[slide_name]
            text_runs = root.findall(".//a:t", NS)
            tx_bodies = root.findall(".//p:txBody", NS)
            shapes = root.findall(".//p:sp", NS)
            picture_items, page_picture_risks = collect_pictures(root)
            pictures = [item[0] for item in picture_items]
            for risk in page_picture_risks:
                picture_geometry_risks.append({"page": page_number, **risk})
            role_counts: dict[str, int] = {}
            page_text_roles: dict[str, int] = {}
            page_non_text_roles: dict[str, int] = {}
            page_picture_roles: dict[str, int] = {}
            page_unknown: list[str] = []

            for shape in shapes:
                name = shape_name(shape, "shape")
                role = shape_role(name)
                increment(role_counts, role)
                increment(total_roles, role)
                has_text = bool(
                    "".join(node.text or "" for node in shape.findall(".//a:t", NS)).strip()
                )
                target = page_text_roles if has_text else page_non_text_roles
                total_target = text_roles if has_text else non_text_roles
                increment(target, role)
                increment(total_target, role)
                if role == "unclassified":
                    display_name = name or "(unnamed shape)"
                    page_unknown.append(display_name)
                    unknown_names.add(display_name)

            picture_coverages = []
            for picture, transform in picture_items:
                name = shape_name(picture, "picture")
                role = shape_role(name)
                increment(role_counts, role)
                increment(total_roles, role)
                increment(page_picture_roles, role)
                increment(picture_roles, role)
                if role == "unclassified":
                    display_name = name or "(unnamed picture)"
                    page_unknown.append(display_name)
                    unknown_names.add(display_name)
                frame = frame_of_picture(picture, transform) if transform is not None else None
                ratio = coverage_ratio(frame, slide_w, slide_h) if frame else None
                picture_coverages.append(
                    {
                        "name": name,
                        "role": role,
                        "frameEmu": frame,
                        "coverageRatio": round(ratio, 6) if ratio is not None else None,
                    }
                )

            ratios = [
                item["coverageRatio"]
                for item in picture_coverages
                if item["coverageRatio"] is not None
            ]
            max_coverage = max(ratios, default=0.0)
            full_slide_risk = max_coverage >= 0.9
            if full_slide_risk:
                full_slide_risk_pages.append(page_number)

            page = {
                "page": page_number,
                "textRunCount": len(text_runs),
                "txBodyCount": len(tx_bodies),
                "shapeCount": len(shapes),
                "pictureCount": len(pictures),
                "shapeRoleCounts": role_counts,
                "textShapeRoleCounts": page_text_roles,
                "nonTextShapeRoleCounts": page_non_text_roles,
                "pictureRoleCounts": page_picture_roles,
                "unknownRoleNames": sorted(set(page_unknown)),
                    "pictureCoverages": picture_coverages,
                    "pictureGeometryRisks": page_picture_risks,
                "maxPictureCoverageRatio": round(max_coverage, 6),
                "fullSlideImageRisk": full_slide_risk,
            }
            pages.append(page)
            for key in totals:
                totals[key] += page[key]

        merged_fonts = set(theme_fonts)
        for values in font_sets.values():
            merged_fonts.update(values)
        has_full_slide_risk = bool(full_slide_risk_pages)
        font_sizes_pt, non_even_font_sizes = collect_font_sizes(root_cache, slide_names)
        return {
            "pptx": str(pptx_path),
            "slideCount": len(slide_names),
            "fontSizesPt": font_sizes_pt,
            "nonEvenFontSizesPt": non_even_font_sizes,
            "slideSizeEmu": {"w": slide_w, "h": slide_h},
            "mediaCount": len(media_names),
            "emptyMediaCount": len(empty_media),
            "emptyMedia": empty_media,
            **{field: sorted(values) for field, values in font_sets.items()},
            "themeFonts": sorted(theme_fonts),
            "unresolvedInheritedFonts": unresolved_fonts,
            "fontFamilies": sorted(merged_fonts),
            "fontFamiliesMeaning": (
                "Union of concrete latin/eastAsian/complexScript/symbol fonts "
                "and concrete theme fonts; unresolved inheritance is separate."
            ),
            **totals,
            "shapeRoleCounts": total_roles,
            "textShapeRoleCounts": text_roles,
            "nonTextShapeRoleCounts": non_text_roles,
            "pictureRoleCounts": picture_roles,
            "unknownRoleNames": sorted(unknown_names),
            "unknownRoleNamesByPage": [
                {"page": page["page"], "names": page["unknownRoleNames"]}
                for page in pages
                if page["unknownRoleNames"]
            ],
            "pages": pages,
            "fullSlideImageRiskPages": full_slide_risk_pages,
            "pictureGeometryRisks": picture_geometry_risks,
            "wholeReferenceImageEmbedded": {
                "status": "risk" if has_full_slide_risk else "notDetected",
                "automatedEvidence": (
                    "At least one picture frame covers 90% or more of a slide."
                    if has_full_slide_risk
                    else "No picture frame covering 90% or more of a slide was detected."
                ),
                "manualEvidenceRequired": True,
                "note": (
                    "Coverage alone cannot prove whether a picture is the original "
                    "reference image; compare it with the reference and asset strategy."
                ),
            },
            "imageOnlyRisk": (
                totals["textRunCount"] == 0
                or totals["txBodyCount"] == 0
                or has_full_slide_risk
            ),
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit editable PPTX structure, fonts, roles, and image risks."
    )
    parser.add_argument("pptx", help="Path to PPTX")
    parser.add_argument("--output", help="Optional JSON output path")
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Print the full JSON to stdout even when --output is given.",
    )
    args = parser.parse_args()

    pptx_path = Path(args.pptx)
    if not pptx_path.exists():
        print(f"PPTX not found: {pptx_path}", file=sys.stderr)
        return 2

    try:
        result = audit(pptx_path)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(f"PPTX audit failed: {exc}", file=sys.stderr)
        return 2
    if args.output:
        write_json(Path(args.output), result)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    # With --output, print only a compact summary by default (the full report is
    # on disk); --print-json forces the full JSON. Without --output, always print
    # the full JSON so nothing is lost (P3-5, aligns with text_frames' summary).
    if args.output and not args.print_json:
        summary_keys = (
            "slideCount",
            "mediaCount",
            "emptyMediaCount",
            "textRunCount",
            "txBodyCount",
            "shapeCount",
            "pictureCount",
            "imageOnlyRisk",
        )
        summary = {key: result[key] for key in summary_keys if key in result}
        summary["fullSlideImageRiskPages"] = result.get("fullSlideImageRiskPages", [])
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
