from __future__ import annotations

import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import run_pipeline  # noqa: E402

FIXTURES = SKILL_ROOT / "tests" / "fixtures"
POWERPNT = Path(r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE")
HAS_PPT = sys.platform == "win32" and POWERPNT.exists()


def test_offline_pipeline_builds_deck(tmp_path):
    result = run_pipeline.run(FIXTURES / "cards-page.html", tmp_path,
                              steps=["extract", "transform", "build"])
    assert result["status"] in ("PASS", "EMPTY")
    assert Path(result["outputPptx"]).exists()
    steps = {s["step"]: s["status"] for s in result["steps"]}
    assert steps["extract"] == "ok" and steps["transform"] == "ok" and steps["build"] == "ok"
    assert (tmp_path / "pipeline-report.json").exists()


def test_offline_pipeline_bakes_svg(tmp_path):
    result = run_pipeline.run(FIXTURES / "svg-table-page.html", tmp_path,
                              steps=["extract", "transform", "build"])
    assert Path(result["outputPptx"]).exists()
    baked = list((tmp_path / "bake").glob("*.png"))
    assert baked, "svg element should have been baked to a PNG"


@pytest.mark.skipif(not HAS_PPT, reason="PowerPoint (Office16) not available")
def test_full_pipeline_double_gate(tmp_path):
    result = run_pipeline.run(FIXTURES / "text-page.html", tmp_path, max_iter=1)
    # 完整链路必须跑通并产出制品；PASS 取决于内容/阈值，PARTIAL 也是合法完成态
    assert result["status"] in ("PASS", "PARTIAL")
    assert Path(result["outputPptx"]).exists()
    assert result["qaReport"] and Path(result["qaReport"]).exists()
    steps = {s["step"] for s in result["steps"]}
    assert {"extract", "transform", "build", "render", "qa"} <= steps
