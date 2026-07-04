from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from PIL import Image

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import extract_html  # noqa: E402

FIXTURES = SKILL_ROOT / "tests" / "fixtures"


@pytest.fixture(scope="module")
def extracted(tmp_path_factory):
    """Extract every fixture once (single browser launch) → {filename: (data, out_dir)}."""
    out = tmp_path_factory.mktemp("extract")
    extract_html.run(FIXTURES, out, "fixed")
    by_name = {}
    for json_path in sorted((out / "extraction").glob("*.json")):
        data = json.loads(json_path.read_text(encoding="utf-8"))
        by_name[Path(data["source"]).name] = data
    return by_name, out


def _elements(data, tag):
    return [e for e in data["elements"] if e["tag"] == tag]


def test_title_geometry_matches_css(extracted):
    data = extracted[0]["text-page.html"]
    title = next(e for e in data["elements"] if e.get("text") and "Hello World Title" in e["text"]["content"])
    assert abs(title["bbox"]["x"] - 80) < 2
    assert abs(title["bbox"]["y"] - 60) < 3
    assert title["text"]["font"]["weight"] == 700


def test_paragraph_wraps_to_two_lines_with_monotonic_y(extracted):
    data = extracted[0]["text-page.html"]
    para = _elements(data, "p")[0]
    lines = para["text"]["lines"]
    assert len(lines) == 2
    assert lines[0]["y"] < lines[1]["y"]


def test_card_gradient_border_radius_shadow(extracted):
    data = extracted[0]["cards-page.html"]
    card = next(e for e in data["elements"] if e["style"]["background"]["type"] == "linear-gradient")
    bg = card["style"]["background"]
    assert [s["color"] for s in bg["stops"]] == ["#ff0000ff", "#0000ffff"]
    assert bg["angle"] == 90
    assert card["style"]["border"]["radius"]["tl"] == 16
    assert card["style"]["border"]["top"]["width"] == 2
    assert card["style"]["border"]["top"]["color"] == "#00ff00ff"
    assert card["style"]["boxShadow"][0]["blur"] == 24
    assert card["style"]["boxShadow"][0]["offsetY"] == 8


def test_rotation_decomposed_to_untransformed_box_and_angle(extracted):
    data = extracted[0]["rotate-page.html"]
    rot = next(e for e in data["elements"] if e["transform"])
    assert abs(rot["transform"]["rot"] - 30) < 0.5
    box = rot["untransformedBox"]
    assert abs(box["w"] - 100) < 2 and abs(box["h"] - 40) < 2
    assert abs(box["x"] - 200) < 2 and abs(box["y"] - 200) < 2


def test_svg_and_table_detected(extracted):
    data = extracted[0]["svg-table-page.html"]
    svg = _elements(data, "svg")
    assert svg and svg[0]["image"]["kind"] == "svg"
    assert _elements(data, "table")
    assert len(_elements(data, "td")) == 4


def test_reference_is_dpr2_png(extracted):
    _, out_dir = extracted
    png = out_dir / "reference" / "page-1.png"
    assert png.exists()
    assert Image.open(png).size == (2560, 1440)


def test_paint_index_is_monotonic(extracted):
    data = extracted[0]["cards-page.html"]
    indices = [e["paintIndex"] for e in data["elements"]]
    assert indices == sorted(indices)
    assert len(set(indices)) == len(indices)


def test_extraction_is_deterministic_after_fonts_ready(tmp_path):
    # Re-extracting a font-bearing page must give identical geometry
    # (document.fonts.ready is awaited before measuring).
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    extract_html.run(FIXTURES / "text-page.html", out_a, "fixed")
    extract_html.run(FIXTURES / "text-page.html", out_b, "fixed")
    da = json.loads((out_a / "extraction" / "page-1.json").read_text(encoding="utf-8"))
    db = json.loads((out_b / "extraction" / "page-1.json").read_text(encoding="utf-8"))
    title_a = next(e for e in da["elements"] if e.get("text") and "Hello" in e["text"]["content"])
    title_b = next(e for e in db["elements"] if e.get("text") and "Hello" in e["text"]["content"])
    assert title_a["bbox"] == title_b["bbox"]
