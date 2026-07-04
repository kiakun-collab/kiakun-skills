#!/usr/bin/env python3
"""M2 · 变换层：extraction.json → layout-spec.json（纯 Python，无浏览器/COM 依赖）。

「干净整洁」目标的实现处：角色分类 → 扁平化合并 → 语义分组 → 可表达性评分 → 文字/字体。
坐标 CSS px，`emuPerPx=9525`。见 references/pipeline-contracts.md。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMA_VERSION = "1.0"
EMU_PER_PX = 9525  # 0.75 * 12700
CLEANLINESS_WARN_RATIO = 1.3

# --- 字体解析 ---------------------------------------------------------------
GENERIC_FALLBACKS = {
    "sans-serif": "Arial", "serif": "Times New Roman", "monospace": "Consolas",
    "system-ui": "Segoe UI", "ui-sans-serif": "Segoe UI", "cursive": "Comic Sans MS",
}
WEB_FONT_MAP = {
    "inter": "Segoe UI", "roboto": "Segoe UI", "open sans": "Segoe UI", "lato": "Segoe UI",
    "montserrat": "Segoe UI", "poppins": "Segoe UI", "nunito": "Segoe UI",
    "helvetica": "Arial", "helvetica neue": "Arial",
    "source han sans sc": "Microsoft YaHei", "noto sans sc": "Microsoft YaHei",
    "pingfang sc": "Microsoft YaHei", "source han serif sc": "SimSun",
}
DEFAULT_INSTALLED = {
    "arial", "segoe ui", "calibri", "times new roman", "consolas", "georgia",
    "tahoma", "verdana", "comic sans ms", "cambria", "microsoft yahei", "simsun", "simhei",
}


def _families(chain: str) -> list[str]:
    return [f.strip().strip("'\"") for f in chain.split(",") if f.strip()]


def resolve_font(chain: str, installed: set[str] | None = None) -> dict:
    installed = installed if installed is not None else DEFAULT_INSTALLED
    for fam in _families(chain):
        low = fam.lower()
        if low in installed:
            return {"source": chain, "target": fam, "confidence": 1.0, "warning": None}
    for fam in _families(chain):
        low = fam.lower()
        mapped = WEB_FONT_MAP.get(low)
        if mapped and mapped.lower() in installed:
            return {"source": chain, "target": mapped, "confidence": 0.8,
                    "warning": f"web font '{fam}' mapped to installed '{mapped}'"}
    for fam in _families(chain):
        low = fam.lower()
        if low in GENERIC_FALLBACKS:
            return {"source": chain, "target": GENERIC_FALLBACKS[low], "confidence": 0.6, "warning": None}
    return {"source": chain, "target": "Arial", "confidence": 0.5,
            "warning": f"no installed match for '{chain}'; falling back to Arial"}


# --- 角色分类 ---------------------------------------------------------------
def _has_visible_box(style: dict) -> bool:
    bg = style["background"]["type"]
    if bg != "none":
        return True
    for side in ("top", "right", "bottom", "left"):
        b = style["border"][side]
        if b["width"] > 0 and b["style"] != "none" and not b["color"].endswith("00"):
            return True
    if style["boxShadow"]:
        return True
    return False


def classify(el: dict) -> str:
    tag = el["tag"]
    if tag in ("html", "body"):
        return "shape" if _has_visible_box(el["style"]) else "structural"
    if el.get("text"):
        return "text"
    if tag == "table":
        return "table"
    if el.get("image"):
        return "svg" if el["image"]["kind"] == "svg" else "image"
    if _has_visible_box(el["style"]):
        return "shape"
    return "structural"


# --- 几何 helper ------------------------------------------------------------
def _round_key(bbox: dict, tol: int = 2) -> tuple:
    return tuple(round(bbox[k] / tol) for k in ("x", "y", "w", "h"))


def _parent_id(eid: str) -> str:
    return eid.rsplit(">", 1)[0] if ">" in eid else ""


def _is_ancestor(anc: str, desc: str) -> bool:
    return desc.startswith(anc + ">")


# --- 样式抽取到 shape 字段 --------------------------------------------------
def _fill(style: dict) -> dict | None:
    bg = style["background"]
    if bg["type"] == "color":
        return {"type": "solid", "color": bg.get("color", "#00000000")}
    if bg["type"] == "linear-gradient":
        return {"type": "linear", "stops": bg["stops"], "angle": bg.get("angle", 90)}
    if bg["type"] == "radial-gradient":
        return {"type": "radial", "stops": bg["stops"]}
    return None


def _line(style: dict) -> dict | None:
    for side in ("top", "right", "bottom", "left"):
        b = style["border"][side]
        if b["width"] > 0 and b["style"] != "none" and not b["color"].endswith("00"):
            dash = {"solid": "solid", "dashed": "dash", "dotted": "dot"}.get(b["style"], "solid")
            return {"width": b["width"], "color": b["color"], "dash": dash}
    return None


def _shadow(style: dict) -> dict | None:
    outer = [s for s in style["boxShadow"] if not s["inset"]]
    if not outer:
        return None
    s = outer[0]
    return {"offsetX": s["offsetX"], "offsetY": s["offsetY"], "blur": s["blur"], "color": s["color"]}


def _radius(style: dict) -> dict | None:
    r = style["border"]["radius"]
    if any(r[k] for k in ("tl", "tr", "br", "bl")):
        return dict(r)
    return None


# --- 可表达性评分 -----------------------------------------------------------
def score_expressibility(role: str, sources: list[dict], svg_as_shapes: bool) -> dict:
    for el in sources:
        if el["rasterize"]["required"]:
            return {"verdict": "baked", "bakedReason": el["rasterize"]["reasons"][0]}
    for el in sources:
        raw = el["style"]["background"].get("raw", "") or ""
        if "conic-gradient" in raw:
            return {"verdict": "baked", "bakedReason": "conic-gradient"}
        shadows = el["style"]["boxShadow"]
        if len([s for s in shadows if not s["inset"]]) > 1:
            return {"verdict": "baked", "bakedReason": "multi-layer-shadow"}
        if any(s["inset"] for s in shadows):
            return {"verdict": "baked", "bakedReason": "inset-shadow"}
    if role == "svg":
        if svg_as_shapes:
            return {"verdict": "native", "bakedReason": None}
        return {"verdict": "baked", "bakedReason": "svg"}
    return {"verdict": "native", "bakedReason": None}


# --- 文字 -------------------------------------------------------------------
def build_text(el: dict, font_map_cache: dict, installed: set[str] | None) -> dict:
    text = el["text"]
    chain = text["font"]["family"]
    if chain not in font_map_cache:
        font_map_cache[chain] = resolve_font(chain, installed)
    resolved = font_map_cache[chain]
    runs = []
    for r in text["runs"]:
        rchain = r.get("family", chain)
        if rchain not in font_map_cache:
            font_map_cache[rchain] = resolve_font(rchain, installed)
        runs.append({
            "text": r["text"],
            "bold": r["bold"], "italic": r["italic"], "color": r["color"],
            "font": font_map_cache[rchain]["target"],
            "sizePt": round(r["sizePx"] * 0.75, 1),
        })
    lines = text["lines"]
    bbox = el["bbox"]
    if lines:
        min_x = min(l["x"] for l in lines)
        min_y = min(l["y"] for l in lines)
        max_r = max(l["x"] + l["w"] for l in lines)
        max_b = max(l["y"] + l["h"] for l in lines)
        padding = {
            "left": max(0, round(min_x - bbox["x"])), "top": max(0, round(min_y - bbox["y"])),
            "right": max(0, round((bbox["x"] + bbox["w"]) - max_r)),
            "bottom": max(0, round((bbox["y"] + bbox["h"]) - max_b)),
        }
    else:
        padding = {"left": 0, "top": 0, "right": 0, "bottom": 0}
    align_map = {"start": "left", "left": "left", "center": "center", "right": "right",
                 "end": "right", "justify": "justify"}
    line_breaks = []
    if text["font"]["whiteSpace"].startswith("pre") and "\n" in text["content"]:
        line_breaks = [i for i, ch in enumerate(text["content"]) if ch == "\n"]
    return {
        "runs": runs,
        "align": align_map.get(text["font"]["align"], "left"),
        "valign": "top",
        "lineBreaks": line_breaks,
        "paddingPx": padding,
        "textLayoutBudget": {"lines": len(lines), "lineWidths": [round(l["w"], 1) for l in lines]},
    }


# --- 主变换 -----------------------------------------------------------------
def transform(extraction: dict, svg_as_shapes: bool = False, installed: set[str] | None = None) -> dict:
    elements = extraction["elements"]
    by_id = {e["id"]: e for e in elements}
    roles = {e["id"]: classify(e) for e in elements}

    structural_ids = [eid for eid, r in roles.items() if r == "structural"]
    visible = [e for e in elements if roles[e["id"]] != "structural"]

    # 1) 同 bounds 的 shape-role 合并（text/image/table/svg 从不被合并掉）
    shape_elems = [e for e in visible if roles[e["id"]] == "shape"]
    merged_out = set()
    merge_groups: dict[tuple, list[dict]] = {}
    for e in shape_elems:
        merge_groups.setdefault(_round_key(e["bbox"]), []).append(e)
    merged_shapes = {}  # primary id -> combined source elements
    for key, group in merge_groups.items():
        group.sort(key=lambda e: e["paintIndex"])
        primary = group[0]
        merged_shapes[primary["id"]] = group
        for other in group[1:]:
            merged_out.add(other["id"])

    # 2) 逐元素产出 shape
    font_map_cache: dict = {}
    shapes = []
    for e in visible:
        eid = e["id"]
        if eid in merged_out:
            continue
        role = roles[eid]
        sources = merged_shapes.get(eid, [e])
        style = e["style"]
        shape = {
            "id": eid,
            "role": role,
            "selectorPath": e.get("selectorPath", ""),
            "bboxPx": dict(e["bbox"]),
            "rot": round(e["transform"]["rot"], 3) if e.get("transform") else 0.0,
            "zOrder": e["paintIndex"],
            "groupId": None,
            "fill": None, "line": None, "shadow": None, "radius": None,
            "text": None, "image": None, "table": None,
            "expressibility": score_expressibility(role, sources, svg_as_shapes),
            "pendingBake": None,
        }
        if e.get("transform") and e.get("untransformedBox"):
            shape["bboxPx"] = dict(e["untransformedBox"])
        # 视觉样式（合并源里取）
        for src in sources:
            shape["fill"] = shape["fill"] or _fill(src["style"])
            shape["line"] = shape["line"] or _line(src["style"])
            shape["shadow"] = shape["shadow"] or _shadow(src["style"])
            shape["radius"] = shape["radius"] or _radius(src["style"])
        if role == "text":
            shape["text"] = build_text(e, font_map_cache, installed)
            shape["fill"] = _fill(style)
            shape["line"] = _line(style)
        elif role in ("image", "svg"):
            img = e["image"]
            shape["image"] = {"src": img.get("currentSrc") or img.get("svg") or img.get("dataUrl"),
                              "objectFit": "cover", "srcRect": None}
        elif role == "table":
            shape["table"] = {"rows": 0, "cols": 0, "colWidthsPx": [], "rowHeightsPx": [], "cells": []}
        if shape["expressibility"]["verdict"] == "baked":
            page = extraction.get("page", 1)
            shape["pendingBake"] = {"selectorPath": e.get("selectorPath", ""),
                                    "targetPng": f"bake/page-{page}-{_safe(eid)}.png"}
        shapes.append(shape)

    # 3) 语义分组：最近的、含≥2 产出的 structural 祖先
    emitted_ids = [s["id"] for s in shapes]
    groups: dict[str, list[str]] = {}
    for s in shapes:
        good = [sid for sid in structural_ids
                if _is_ancestor(sid, s["id"]) and sum(1 for eid in emitted_ids if _is_ancestor(sid, eid)) >= 2]
        if good:
            nearest = max(good, key=len)
            s["groupId"] = nearest
            groups.setdefault(nearest, []).append(s["id"])

    group_list = [{"id": gid, "children": children,
                   "label": by_id[gid]["tag"] if gid in by_id else "group"}
                  for gid, children in groups.items()]

    shapes.sort(key=lambda s: s["zOrder"])
    visible_count = len(visible)
    emitted_count = len(shapes)
    ratio = round(emitted_count / visible_count, 3) if visible_count else 0.0
    warnings = []
    if ratio > CLEANLINESS_WARN_RATIO:
        warnings.append(f"cleanliness ratio {ratio} > {CLEANLINESS_WARN_RATIO}")
    font_map = list(font_map_cache.values())
    for fm in font_map:
        if fm["warning"]:
            warnings.append(fm["warning"])

    return {
        "schemaVersion": SCHEMA_VERSION,
        "page": extraction.get("page", 1),
        "mode": "html-to-pptx",
        "coordinateSystem": {"unit": "csspx", "width": 1280, "height": 720, "emuPerPx": EMU_PER_PX},
        "reference": extraction.get("reference"),
        "cleanliness": {"emittedShapes": emitted_count, "visibleElements": visible_count, "ratio": ratio},
        "fontMap": font_map,
        "warnings": warnings,
        "shapes": shapes,
        "groups": group_list,
    }


def _safe(eid: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in eid)[-60:]


def make_stdout_robust() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extraction", help="extraction.json path")
    parser.add_argument("--output", required=True)
    parser.add_argument("--svg-as-shapes", action="store_true",
                        help="Attempt native freeform for simple SVG (risk自担).")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    src = Path(args.extraction)
    try:
        extraction = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    spec = transform(extraction, svg_as_shapes=args.svg_as_shapes)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    make_stdout_robust()
    if args.json:
        print(json.dumps(spec["cleanliness"], ensure_ascii=False))
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
