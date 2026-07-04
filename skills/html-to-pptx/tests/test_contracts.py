from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import build_layout_spec as bl  # noqa: E402

CONTRACTS = (SKILL_ROOT / "references" / "pipeline-contracts.md").read_text(encoding="utf-8")
SKILL = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")


def _min_extraction():
    return {
        "schemaVersion": "1.0", "page": 1, "source": "x.html",
        "viewport": {"width": 1280, "height": 720, "dpr": 2},
        "coordinateSystem": {"unit": "csspx", "width": 1280, "height": 720},
        "reference": "reference/page-1.png",
        "elements": [{
            "id": "html>body:nth-of-type(1)>div:nth-of-type(1)", "tag": "div", "paintIndex": 0,
            "bbox": {"x": 0, "y": 0, "w": 100, "h": 50}, "untransformedBox": None, "transform": None,
            "style": {"background": {"raw": "rgb(0,0,0)", "type": "color", "color": "#000000ff"},
                      "border": {"top": {"width": 0, "color": "#00000000", "style": "none"},
                                 "right": {"width": 0, "color": "#00000000", "style": "none"},
                                 "bottom": {"width": 0, "color": "#00000000", "style": "none"},
                                 "left": {"width": 0, "color": "#00000000", "style": "none"},
                                 "radius": {"tl": 0, "tr": 0, "br": 0, "bl": 0}},
                      "boxShadow": [], "opacity": 1.0, "overflow": "visible", "zIndex": "auto", "mixBlendMode": "normal"},
            "text": None, "image": None, "rasterize": {"required": False, "reasons": []},
            "selectorPath": "html > body > div:nth-of-type(1)"}],
    }


def test_layout_spec_top_level_keys_are_documented():
    spec = bl.transform(_min_extraction())
    for key in spec:
        assert key in CONTRACTS, f"layout-spec key '{key}' missing from pipeline-contracts.md"


def test_layout_spec_shape_keys_are_documented():
    spec = bl.transform(_min_extraction())
    for key in spec["shapes"][0]:
        assert key in CONTRACTS, f"shape key '{key}' missing from contracts"


def test_extraction_and_qa_and_pipeline_report_fields_documented():
    for field in ("schemaVersion", "elements", "paintIndex", "untransformedBox", "rasterize", "selectorPath"):
        assert field in CONTRACTS
    for field in ("overallStatus", "autoIterationCount", "calibrationStatus", "defects", "bakedElements"):
        assert field in CONTRACTS
    for field in ("pipeline-report.json", "outputPptx", "qaReport"):
        assert field in CONTRACTS


def test_coordinate_and_exit_code_contract():
    assert "9525" in CONTRACTS
    assert "1280" in CONTRACTS and "720" in CONTRACTS
    assert "`0`" in CONTRACTS and "`1`" in CONTRACTS and "`2`" in CONTRACTS


def test_skill_description_states_triggers():
    assert "html-to-pptx" in SKILL
    assert "HTML" in SKILL and "PPTX" in SKILL and "editable" in SKILL
    assert "16:9" in SKILL
