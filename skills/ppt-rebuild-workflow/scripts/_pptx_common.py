#!/usr/bin/env python3
"""Shared OOXML helpers for the PPTX audit scripts.

Extracted from ``audit_pptx_text_frames.py`` and ``audit_pptx_structure.py``
(P1-1). These helpers are byte-for-byte equivalent to the former per-script
copies; the audit outputs must remain identical.
"""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


def slide_sort_key(name: str) -> int:
    match = re.search(r"slide(\d+)\.xml$", name)
    return int(match.group(1)) if match else 0


def shape_name(shape: ET.Element, kind: str | None = None) -> str:
    """Return the shape's authoring name.

    ``kind`` selects the non-visual property container:
    ``"shape"`` -> ``p:nvSpPr``, ``"picture"`` -> ``p:nvPicPr``. When ``kind``
    is ``None`` the container is inferred from the element tag (connectors use
    ``p:nvCxnSpPr``, everything else ``p:nvSpPr``) -- the behaviour previously
    implemented in ``audit_pptx_text_frames.py``.
    """
    if kind == "picture":
        node = shape.find("./p:nvPicPr/p:cNvPr", NS)
    elif kind == "shape":
        node = shape.find("./p:nvSpPr/p:cNvPr", NS)
    elif shape.tag.endswith("cxnSp"):
        node = shape.find("./p:nvCxnSpPr/p:cNvPr", NS)
    else:
        node = shape.find("./p:nvSpPr/p:cNvPr", NS)
    return node.attrib.get("name", "") if node is not None else ""


def group_transform(
    group: ET.Element,
    parent: tuple[float, float, float, float],
) -> tuple[tuple[float, float, float, float] | None, str | None]:
    xfrm = group.find("./p:grpSpPr/a:xfrm", NS)
    if xfrm is None:
        return None, "group has no transform"
    if int(xfrm.attrib.get("rot", "0")):
        return None, "rotated group transform is not resolved"
    off = xfrm.find("./a:off", NS)
    ext = xfrm.find("./a:ext", NS)
    child_off = xfrm.find("./a:chOff", NS)
    child_ext = xfrm.find("./a:chExt", NS)
    if None in (off, ext, child_off, child_ext):
        return None, "group transform is incomplete"
    child_w = float(child_ext.attrib.get("cx", "0"))
    child_h = float(child_ext.attrib.get("cy", "0"))
    if child_w == 0 or child_h == 0:
        return None, "group child extent is zero"
    local_sx = float(ext.attrib.get("cx", "0")) / child_w
    local_sy = float(ext.attrib.get("cy", "0")) / child_h
    local_tx = float(off.attrib.get("x", "0")) - float(child_off.attrib.get("x", "0")) * local_sx
    local_ty = float(off.attrib.get("y", "0")) - float(child_off.attrib.get("y", "0")) * local_sy
    parent_sx, parent_sy, parent_tx, parent_ty = parent
    return (
        (
            parent_sx * local_sx,
            parent_sy * local_sy,
            parent_tx + parent_sx * local_tx,
            parent_ty + parent_sy * local_ty,
        ),
        None,
    )
