from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import qa_gate  # noqa: E402

W2, H2 = 2560, 1440  # @2x canvas


def _canvas():
    return Image.new("RGB", (W2, H2), "white")


def _spec(shapes, page=1):
    return {
        "schemaVersion": "1.0", "page": page, "mode": "html-to-pptx",
        "coordinateSystem": {"unit": "csspx", "width": 1280, "height": 720, "emuPerPx": 9525},
        "cleanliness": {}, "fontMap": [], "warnings": [], "shapes": shapes, "groups": [],
    }


def _shape(sid, role, x, y, w, h, **kw):
    s = {"id": sid, "role": role, "bboxPx": {"x": x, "y": y, "w": w, "h": h},
         "expressibility": {"verdict": "native", "bakedReason": None}, "text": None}
    s.update(kw)
    return s


@pytest.fixture
def scene(tmp_path):
    ref_dir = tmp_path / "reference"
    rnd_dir = tmp_path / "render"
    spec_dir = tmp_path / "spec"
    for d in (ref_dir, rnd_dir, spec_dir):
        d.mkdir()

    def build(defect_color=None, extra_line=False):
        ref = _canvas()
        ImageDraw.Draw(ref).rectangle([200, 200, 600, 400], fill="#3366cc")  # element e1 (css 100,100,200,100)
        ImageDraw.Draw(ref).rectangle([200, 600, 900, 640], fill="#111111")  # text band (css 100,300,350,20)
        ref.save(ref_dir / "page-1.png")

        rnd = _canvas()
        ImageDraw.Draw(rnd).rectangle([200, 200, 600, 400], fill=(defect_color or "#3366cc"))
        ImageDraw.Draw(rnd).rectangle([200, 600, 900, 640], fill="#111111")
        if extra_line:
            ImageDraw.Draw(rnd).rectangle([200, 680, 900, 720], fill="#111111")  # second text line
        rnd.save(rnd_dir / "page-1.png")

        spec = _spec([
            _shape("e1", "shape", 100, 100, 200, 100),
            _shape("t1", "text", 100, 300, 350, 60,
                   text={"textLayoutBudget": {"lines": 1, "lineWidths": [350]},
                         "runs": [{"text": "x"}], "align": "left", "valign": "top",
                         "lineBreaks": [], "paddingPx": {"left": 0, "top": 0, "right": 0, "bottom": 0}}),
        ])
        (spec_dir / "page-1.json").write_text(json.dumps(spec), encoding="utf-8")
        return ref_dir, rnd_dir, spec_dir

    return build, tmp_path


def test_identical_render_passes(scene):
    build, tmp = scene
    ref, rnd, spec = build()
    report = qa_gate.run_qa(ref, rnd, spec, tmp / "qa.json")
    assert report["overallStatus"] == "PASS"
    assert report["pages"][0]["ssim"] >= 0.93
    assert report["pages"][0]["defects"] == []


def test_element_color_difference_flags_defect(scene):
    build, tmp = scene
    ref, rnd, spec = build(defect_color="#cc0000")
    report = qa_gate.run_qa(ref, rnd, spec, tmp / "qa.json")
    ids = {d["id"] for d in report["pages"][0]["defects"]}
    assert "e1" in ids


def test_text_wrap_mismatch_flagged(scene):
    build, tmp = scene
    ref, rnd, spec = build(extra_line=True)
    report = qa_gate.run_qa(ref, rnd, spec, tmp / "qa.json")
    page = report["pages"][0]
    assert not page["textLineConsistency"]
    assert any(d["type"] == "text-wrap" for d in page["defects"])


def test_ssim_self_compare_is_one():
    import numpy as np
    a = np.asarray(Image.new("L", (64, 64), 128), dtype=np.float64)
    assert qa_gate.ssim(a, a) > 0.999


def test_defect_action_classification():
    assert qa_gate.classify_defect_action({"type": "visual"}) == "bake-element-downgrade"
    assert qa_gate.classify_defect_action({"type": "text-wrap"}) == "widen-textbox-2pct"
    assert qa_gate.classify_defect_action({"type": "position"}) == "translate-and-rebuild"


def test_toolkit_missing_raises(monkeypatch):
    monkeypatch.setenv("HTML2PPTX_QA_TOOLKIT", str(SKILL_ROOT / "does-not-exist"))
    with pytest.raises(SystemExit):
        qa_gate.resolve_toolkit()


def test_repair_widens_text_and_bakes_visual_but_never_bakes_text():
    spec = _spec([
        _shape("t1", "text", 100, 100, 300, 40,
               text={"textLayoutBudget": {"lines": 1, "lineWidths": [300]}, "runs": [], "align": "left",
                     "valign": "top", "lineBreaks": [], "paddingPx": {"left": 0, "top": 0, "right": 0, "bottom": 0}}),
        _shape("v1", "shape", 0, 0, 200, 200, pendingBake=None, selectorPath="html > body > div:nth-of-type(1)"),
    ])
    defects = [{"id": "t1", "type": "text-wrap"}, {"id": "v1", "type": "visual"}]
    applied = qa_gate.apply_repairs(spec, defects)
    by_id = {s["id"]: s for s in spec["shapes"]}
    assert by_id["t1"]["bboxPx"]["w"] == 306.0  # 300 * 1.02
    assert by_id["t1"]["expressibility"]["verdict"] == "native"  # 文字绝不烘焙
    assert by_id["v1"]["expressibility"] == {"verdict": "baked", "bakedReason": "qa-downgrade"}
    assert by_id["v1"]["pendingBake"] is not None
    assert set(applied) == {"widen-textbox:t1", "bake-downgrade:v1"}
