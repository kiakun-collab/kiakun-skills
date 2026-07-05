from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import build_layout_spec as bl  # noqa: E402


def _side(width=0, color="#00000000", style="none"):
    return {"width": width, "color": color, "style": style}


def elem(eid, tag, x, y, w, h, paint=0):
    return {
        "id": eid, "tag": tag, "paintIndex": paint,
        "bbox": {"x": x, "y": y, "w": w, "h": h},
        "untransformedBox": None, "transform": None,
        "style": {
            "background": {"raw": "", "type": "none"},
            "border": {"top": _side(), "right": _side(), "bottom": _side(), "left": _side(),
                       "radius": {"tl": 0, "tr": 0, "br": 0, "bl": 0}},
            "boxShadow": [], "opacity": 1.0, "overflow": "visible", "zIndex": "auto", "mixBlendMode": "normal",
        },
        "text": None, "image": None,
        "rasterize": {"required": False, "reasons": []},
        "selectorPath": eid.replace(">", " > "),
    }


def text_el(eid, tag, x, y, w, h, content, family="Arial, sans-serif", size=20, paint=0):
    e = elem(eid, tag, x, y, w, h, paint)
    e["text"] = {
        "content": content,
        "lines": [{"x": x, "y": y, "w": w, "h": 24, "text": content}],
        "runs": [{"text": content, "bold": False, "italic": False, "color": "#111111FF",
                  "sizePx": size, "family": family, "weight": 400, "style": "normal"}],
        "font": {"family": family, "sizePx": size, "weight": 400, "style": "normal",
                 "lineHeightPx": size * 1.2, "letterSpacingPx": 0, "color": "#111111FF",
                 "align": "left", "whiteSpace": "normal"},
    }
    return e


def spec(elements, **kw):
    return bl.transform({"page": 1, "elements": elements}, **kw)


# --- 同 bounds 合并 ---------------------------------------------------------
def test_same_bounds_three_layers_merge_to_one_shape():
    outer = elem("html>body:nth-of-type(1)>div:nth-of-type(1)", "div", 100, 100, 200, 100, 0)
    outer["style"]["background"] = {"raw": "rgb(255,0,0)", "type": "color", "color": "#ff0000ff"}
    middle = elem("html>body:nth-of-type(1)>div:nth-of-type(1)>div:nth-of-type(1)", "div", 100, 100, 200, 100, 1)
    middle["style"]["border"]["top"] = _side(2, "#00ff00ff", "solid")
    inner = elem("html>body:nth-of-type(1)>div:nth-of-type(1)>div:nth-of-type(1)>div:nth-of-type(1)", "div", 100, 100, 200, 100, 2)
    inner["style"]["boxShadow"] = [{"offsetX": 0, "offsetY": 4, "blur": 12, "spread": 0, "color": "#00000040", "inset": False}]

    result = spec([outer, middle, inner])
    shapes = result["shapes"]
    assert len(shapes) == 1
    s = shapes[0]
    assert s["fill"]["color"] == "#ff0000ff"
    assert s["line"]["width"] == 2
    assert s["shadow"]["blur"] == 12


# --- wrapper 不产出 + 分组 --------------------------------------------------
def test_structural_wrapper_dropped_but_children_grouped():
    wrapper = elem("html>body:nth-of-type(1)>div:nth-of-type(1)", "div", 0, 0, 500, 300, 0)
    a = text_el("html>body:nth-of-type(1)>div:nth-of-type(1)>p:nth-of-type(1)", "p", 10, 10, 100, 24, "A", paint=1)
    b = text_el("html>body:nth-of-type(1)>div:nth-of-type(1)>p:nth-of-type(2)", "p", 10, 50, 100, 24, "B", paint=2)

    result = spec([wrapper, a, b])
    ids = [s["id"] for s in result["shapes"]]
    assert wrapper["id"] not in ids
    assert len(result["shapes"]) == 2
    for s in result["shapes"]:
        assert s["groupId"] == wrapper["id"]
    assert len(result["groups"]) == 1
    assert set(result["groups"][0]["children"]) == {a["id"], b["id"]}


# --- backdrop-filter → baked ------------------------------------------------
def test_backdrop_filter_is_baked_with_reason():
    e = elem("html>body:nth-of-type(1)>div:nth-of-type(1)", "div", 0, 0, 200, 100, 0)
    e["style"]["background"] = {"raw": "rgba(255,255,255,0.2)", "type": "color", "color": "#ffffff33"}
    e["rasterize"] = {"required": True, "reasons": ["backdrop-filter"]}
    s = spec([e])["shapes"][0]
    assert s["expressibility"]["verdict"] == "baked"
    assert s["expressibility"]["bakedReason"] == "backdrop-filter"
    assert s["pendingBake"] is not None
    assert s["pendingBake"]["targetPng"].startswith("bake/page-1-")


def test_multi_layer_shadow_is_baked():
    e = elem("html>body:nth-of-type(1)>div:nth-of-type(1)", "div", 0, 0, 200, 100, 0)
    e["style"]["background"] = {"raw": "rgb(0,0,0)", "type": "color", "color": "#000000ff"}
    e["style"]["boxShadow"] = [
        {"offsetX": 0, "offsetY": 2, "blur": 4, "spread": 0, "color": "#00000040", "inset": False},
        {"offsetX": 0, "offsetY": 8, "blur": 16, "spread": 0, "color": "#00000020", "inset": False},
    ]
    s = spec([e])["shapes"][0]
    assert s["expressibility"] == {"verdict": "baked", "bakedReason": "multi-layer-shadow"}


# --- 字体映射 ---------------------------------------------------------------
def test_font_installed_hit():
    r = bl.resolve_font("Arial, sans-serif")
    assert r["target"] == "Arial" and r["confidence"] == 1.0 and r["warning"] is None


def test_font_webfont_mapped_with_warning():
    r = bl.resolve_font("Inter, system-ui, sans-serif")
    assert r["target"] == "Segoe UI" and r["confidence"] == 0.8 and "Inter" in r["warning"]


def test_font_unknown_falls_back_to_arial_with_warning():
    r = bl.resolve_font("Totally Made Up Face", installed={"arial"})
    assert r["target"] == "Arial" and r["confidence"] == 0.5 and r["warning"]


def test_font_corrects_missing_space_to_registered_name():
    # retrospective 5.1: 写 "腾讯体W7" 实际注册名是 "腾讯体 W7"，应自动校正。
    r = bl.resolve_font("腾讯体W7", installed={"腾讯体 W7"})
    assert r["target"] == "腾讯体 W7"
    assert r["confidence"] == 0.9
    assert "校正" in r["warning"]


def test_font_hit_returns_registered_casing():
    r = bl.resolve_font("arial", installed={"Arial"})
    assert r["target"] == "Arial" and r["confidence"] == 1.0


def test_font_fallback_warns_about_powerpoint_fallback():
    r = bl.resolve_font("Nonexistent Face", installed={"Arial"})
    assert r["confidence"] == 0.5 and "fallback" in r["warning"].lower()


def test_installed_fonts_enumeration_returns_names():
    fonts = bl.load_installed_fonts()
    assert isinstance(fonts, frozenset) and len(fonts) >= 1


def test_out_of_bounds_element_warns():
    e = elem("html>body:nth-of-type(1)>div:nth-of-type(1)", "div", 1200, 600, 200, 200, 0)
    e["style"]["background"] = {"raw": "rgb(0,0,0)", "type": "color", "color": "#000000ff"}
    result = spec([e])
    assert any("超出" in w for w in result["warnings"])


def test_text_shape_maps_font_and_size_to_pt():
    e = text_el("html>body:nth-of-type(1)>p:nth-of-type(1)", "p", 10, 10, 200, 24, "Hi", family="Inter, sans-serif", size=20)
    result = spec([e])
    s = result["shapes"][0]
    assert s["role"] == "text"
    assert s["text"]["runs"][0]["font"] == "Segoe UI"
    assert s["text"]["runs"][0]["sizePt"] == 15.0  # 20 * 0.75
    assert any("Inter" in w for w in result["warnings"])


# --- cleanliness ratio ------------------------------------------------------
def test_cleanliness_ratio_reflects_merge():
    els = []
    for i in range(3):
        e = elem(f"html>body:nth-of-type(1)>div:nth-of-type({i + 1})", "div", 100, 100, 200, 100, i)
        e["style"]["background"] = {"raw": "rgb(0,0,0)", "type": "color", "color": "#000000ff"}
        els.append(e)
    result = spec(els)
    assert result["cleanliness"]["visibleElements"] == 3
    assert result["cleanliness"]["emittedShapes"] == 1
    assert result["cleanliness"]["ratio"] == round(1 / 3, 3)


def test_rotation_uses_untransformed_box():
    e = elem("html>body:nth-of-type(1)>div:nth-of-type(1)", "div", 180, 190, 120, 60, 0)
    e["style"]["background"] = {"raw": "rgb(0,0,0)", "type": "color", "color": "#000000ff"}
    e["transform"] = {"matrix": [0.87, 0.5, -0.5, 0.87, 0, 0], "rot": 30.0, "scaleX": 1, "scaleY": 1, "translateX": 0, "translateY": 0}
    e["untransformedBox"] = {"x": 200, "y": 200, "w": 100, "h": 40}
    s = spec([e])["shapes"][0]
    assert s["rot"] == 30.0
    assert s["bboxPx"] == {"x": 200, "y": 200, "w": 100, "h": 40}
