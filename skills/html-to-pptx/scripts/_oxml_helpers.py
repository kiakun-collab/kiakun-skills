#!/usr/bin/env python3
"""M3 · 直接操作 OOXML 的 helper（python-pptx 渐变/阴影/透明度支持弱处）。

每个 helper 只拼最小 XML；由 test_build.py 的 zipfile+lxml 断言覆盖。
"""

from __future__ import annotations

from pptx.oxml.ns import qn
from pptx.oxml import parse_xml

A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _hex_rgb(hex8: str) -> str:
    """#RRGGBBAA / #RRGGBB → 'RRGGBB'（大写，无 #）。"""
    h = hex8.lstrip("#")
    return h[:6].upper()


def _alpha_pct(hex8: str) -> int | None:
    """返回 1000ths-of-percent 的 alpha；不透明（FF/缺省）返回 None。"""
    h = hex8.lstrip("#")
    if len(h) < 8:
        return None
    a = int(h[6:8], 16)
    if a >= 255:
        return None
    return round(a / 255 * 100000)


def _srgb(hex8: str) -> str:
    alpha = _alpha_pct(hex8)
    inner = f'<a:alpha val="{alpha}"/>' if alpha is not None else ""
    return f'<a:srgbClr val="{_hex_rgb(hex8)}">{inner}</a:srgbClr>' if inner else f'<a:srgbClr val="{_hex_rgb(hex8)}"/>'


def _spPr(shape):
    return shape._element.spPr


def _remove(spPr, tags):
    for tag in tags:
        for el in spPr.findall(qn(tag)):
            spPr.remove(el)


FILL_TAGS = ("a:noFill", "a:solidFill", "a:gradFill", "a:blipFill", "a:pattFill", "a:grpFill")


def set_solid_fill(shape, hex8: str) -> None:
    _remove(_spPr(shape), FILL_TAGS)
    xml = f'<a:solidFill xmlns:a="{A}">{_srgb(hex8)}</a:solidFill>'
    _insert_fill(shape, xml)


def css_angle_to_ooxml(angle_deg: float) -> int:
    """CSS 线性渐变角度 → OOXML lin ang（60000ths deg，顺时针，0=东）。"""
    ooxml = (angle_deg - 90) % 360
    return int(round(ooxml * 60000))


def set_gradient_fill(shape, stops: list[dict], angle_deg: float) -> None:
    _remove(_spPr(shape), FILL_TAGS)
    gs = "".join(
        f'<a:gs pos="{int(round((s["offset"] or 0) * 100000))}">{_srgb(s["color"])}</a:gs>'
        for s in stops
    )
    ang = css_angle_to_ooxml(angle_deg)
    xml = (
        f'<a:gradFill xmlns:a="{A}"><a:gsLst>{gs}</a:gsLst>'
        f'<a:lin ang="{ang}" scaled="1"/></a:gradFill>'
    )
    _insert_fill(shape, xml)


def _insert_fill(shape, xml: str) -> None:
    spPr = _spPr(shape)
    element = parse_xml(xml)
    # fill 必须在 a:ln 之前（schema 顺序）
    ln = spPr.find(qn("a:ln"))
    if ln is not None:
        ln.addprevious(element)
    else:
        spPr.append(element)


def set_outer_shadow(shape, offset_x: float, offset_y: float, blur: float, hex8: str) -> None:
    """写 <a:effectLst><a:outerShdw>；距离/模糊单位 EMU。"""
    import math

    dist = int(round(math.hypot(offset_x, offset_y) * 9525))
    direction = int(round((math.degrees(math.atan2(offset_y, offset_x)) % 360) * 60000))
    blur_emu = int(round(blur * 9525))
    xml = (
        f'<a:effectLst xmlns:a="{A}"><a:outerShdw blurRad="{blur_emu}" dist="{dist}" '
        f'dir="{direction}" rotWithShape="0">{_srgb(hex8)}</a:outerShdw></a:effectLst>'
    )
    spPr = _spPr(shape)
    _remove(spPr, ("a:effectLst",))
    spPr.append(parse_xml(xml))


def disable_autofit(text_frame) -> None:
    """确保 bodyPr 里是 <a:noAutofit/>（关自动缩放，防折行漂移）。"""
    bodyPr = text_frame._txBody.bodyPr
    for tag in ("a:normAutofit", "a:spAutoFit", "a:noAutofit"):
        for el in bodyPr.findall(qn(tag)):
            bodyPr.remove(el)
    bodyPr.append(parse_xml(f'<a:noAutofit xmlns:a="{A}"/>'))


def set_rounded_adj(shape, radius_px: float, shorter_side_px: float) -> None:
    """roundRect 圆角比例：adj = radius / (较短边)。"""
    if shorter_side_px <= 0:
        return
    frac = max(0.0, min(0.5, radius_px / shorter_side_px))
    val = int(round(frac * 100000))
    spPr = _spPr(shape)
    prstGeom = spPr.find(qn("a:prstGeom"))
    if prstGeom is None:
        return
    for av in prstGeom.findall(qn("a:avLst")):
        prstGeom.remove(av)
    prstGeom.append(parse_xml(f'<a:avLst xmlns:a="{A}"><a:gd name="adj" fmla="val {val}"/></a:avLst>'))
