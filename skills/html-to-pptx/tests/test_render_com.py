from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import build_pptx  # noqa: E402

POWERPNT = Path(r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE")
HAS_PPT = sys.platform == "win32" and POWERPNT.exists()

pytestmark = pytest.mark.skipif(not HAS_PPT, reason="PowerPoint (Office16) not available")


def _tiny_deck(tmp_path):
    spec = {
        "schemaVersion": "1.0", "page": 1, "mode": "html-to-pptx",
        "coordinateSystem": {"unit": "csspx", "width": 1280, "height": 720, "emuPerPx": 9525},
        "reference": None, "cleanliness": {}, "fontMap": [], "warnings": [], "groups": [],
        "shapes": [
            {"id": "bg", "role": "shape", "bboxPx": {"x": 0, "y": 0, "w": 1280, "h": 720},
             "rot": 0.0, "zOrder": 0, "groupId": None,
             "fill": {"type": "solid", "color": "#ffffffff"}, "line": None, "shadow": None,
             "radius": None, "text": None, "image": None, "table": None,
             "expressibility": {"verdict": "native", "bakedReason": None}, "pendingBake": None},
            {"id": "t", "role": "text", "bboxPx": {"x": 100, "y": 100, "w": 600, "h": 80},
             "rot": 0.0, "zOrder": 1, "groupId": None, "fill": None, "line": None, "shadow": None,
             "radius": None, "image": None, "table": None,
             "expressibility": {"verdict": "native", "bakedReason": None}, "pendingBake": None,
             "text": {"runs": [{"text": "COM render", "bold": True, "italic": False,
                                "color": "#112233FF", "font": "Arial", "sizePt": 32.0}],
                      "align": "left", "valign": "top", "lineBreaks": [],
                      "paddingPx": {"left": 4, "top": 4, "right": 4, "bottom": 4},
                      "textLayoutBudget": {"lines": 1, "lineWidths": [400]}}},
        ],
    }
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    pptx = tmp_path / "deck.pptx"
    build_pptx.build([spec_path], pptx)
    return pptx


def test_com_export_is_2560x1440_and_no_zombie(tmp_path):
    import psutil
    from PIL import Image

    import render_pptx_com

    pptx = _tiny_deck(tmp_path)
    out = tmp_path / "render"
    before = {p.pid for p in psutil.process_iter(["name"]) if (p.info["name"] or "").lower() == "powerpnt.exe"}
    pngs = render_pptx_com.render(pptx, out, scale=2)
    assert len(pngs) == 1
    assert Image.open(pngs[0]).size == (2560, 1440)
    after = {p.pid for p in psutil.process_iter(["name"]) if (p.info["name"] or "").lower() == "powerpnt.exe"}
    # our launched instance must not leak
    assert after <= before
