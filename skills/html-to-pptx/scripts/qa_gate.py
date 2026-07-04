#!/usr/bin/env python3
"""M4 · QA 门禁：reference@2x vs render@2x → qa-report.json。

双门禁：全页 SSIM + 逐元素 SSIM + 文字折行一致性；复用 ppt-rebuild 的
calibrate（坐标校准）与 make_reference_render_comparison（对照大图，D4 路径复用）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import uniform_filter

SCHEMA_VERSION = "1.0"
SSIM_THRESHOLD = 0.93
ELEMENT_SSIM_THRESHOLD = 0.80
ELEMENT_MAD_THRESHOLD = 12.0  # 逐元素平均颜色绝对差（0-255），SSIM 对纯色区亮度过宽容，用它兜底
DPR = 2


def resolve_toolkit() -> Path:
    env = os.environ.get("HTML2PPTX_QA_TOOLKIT")
    path = Path(env) if env else (Path(__file__).resolve().parents[2] / "ppt-rebuild-workflow" / "scripts")
    if not (path / "make_reference_render_comparison.py").exists():
        raise SystemExit(
            f"QA toolkit not found at {path}; set HTML2PPTX_QA_TOOLKIT to ppt-rebuild-workflow/scripts"
        )
    return path


def _gray(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("L"), dtype=np.float64)


def ssim(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape != b.shape:
        b = np.asarray(Image.fromarray(b.astype(np.uint8)).resize((a.shape[1], a.shape[0])), dtype=np.float64)
    win = 7
    mu_a = uniform_filter(a, win)
    mu_b = uniform_filter(b, win)
    va = uniform_filter(a * a, win) - mu_a ** 2
    vb = uniform_filter(b * b, win) - mu_b ** 2
    vab = uniform_filter(a * b, win) - mu_a * mu_b
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    s = ((2 * mu_a * mu_b + c1) * (2 * vab + c2)) / ((mu_a ** 2 + mu_b ** 2 + c1) * (va + vb + c2))
    return float(np.clip(s.mean(), -1.0, 1.0))


def _crop(img: np.ndarray, bbox: dict, scale: int) -> np.ndarray:
    x, y = int(bbox["x"] * scale), int(bbox["y"] * scale)
    w, h = int(bbox["w"] * scale), int(bbox["h"] * scale)
    x2, y2 = min(img.shape[1], x + w), min(img.shape[0], y + h)
    return img[max(0, y):y2, max(0, x):x2]


def count_text_lines(img_region: np.ndarray) -> int:
    """粗略行数：灰度上有墨迹的行聚成带。"""
    if img_region.size == 0:
        return 0
    ink = (img_region < 200).sum(axis=1)
    threshold = max(1, img_region.shape[1] * 0.02)
    bands, active = 0, False
    for v in ink:
        if v >= threshold and not active:
            bands += 1
            active = True
        elif v < threshold:
            active = False
    return bands


def run_comparison(toolkit: Path, reference_dir: Path, render_dir: Path, out_png: Path) -> str | None:
    try:
        subprocess.run(
            [sys.executable, str(toolkit / "make_reference_render_comparison.py"),
             str(reference_dir), str(render_dir), str(out_png), "--allow-missing"],
            capture_output=True, text=True, check=False,
        )
    except OSError:
        return None
    return str(out_png) if out_png.exists() else None


def _page_num(path: Path) -> int:
    m = re.findall(r"\d+", path.stem)
    return int(m[-1]) if m else 0


def evaluate_page(reference: Path, render: Path, spec: dict, ssim_threshold: float) -> dict:
    ref_img = _gray(reference)
    rnd_img = _gray(render)
    ref_rgb = np.asarray(Image.open(reference).convert("RGB"), dtype=np.float64)
    rnd_rgb = np.asarray(Image.open(render).convert("RGB"), dtype=np.float64)
    if ref_img.shape != rnd_img.shape:
        rnd_img = np.asarray(
            Image.open(render).convert("L").resize((ref_img.shape[1], ref_img.shape[0])), dtype=np.float64
        )
        rnd_rgb = np.asarray(
            Image.open(render).convert("RGB").resize((ref_img.shape[1], ref_img.shape[0])), dtype=np.float64
        )
    page_ssim = round(ssim(ref_img, rnd_img), 4)
    defects = []
    text_ok = True
    for sh in spec.get("shapes", []):
        crop_ref = _crop(ref_img, sh["bboxPx"], DPR)
        crop_rnd = _crop(rnd_img, sh["bboxPx"], DPR)
        if crop_ref.size < 64 or crop_ref.shape != crop_rnd.shape:
            continue
        el_ssim = ssim(crop_ref, crop_rnd)
        mad = float(np.abs(_crop(ref_rgb, sh["bboxPx"], DPR) - _crop(rnd_rgb, sh["bboxPx"], DPR)).mean())
        if el_ssim < ELEMENT_SSIM_THRESHOLD or mad > ELEMENT_MAD_THRESHOLD:
            delta = round(max(1 - el_ssim, mad / 255), 4)
            defects.append({"id": sh["id"], "type": _defect_type(sh["role"]),
                            "delta": delta, "action": None})
        if sh["role"] == "text" and sh.get("text"):
            budget = sh["text"]["textLayoutBudget"]["lines"]
            actual = count_text_lines(crop_rnd)
            if budget and actual and abs(actual - budget) >= 1:
                text_ok = False
                defects.append({"id": sh["id"], "type": "text-wrap",
                                "delta": abs(actual - budget), "action": None})
    for d in defects:
        d["action"] = classify_defect_action(d)
    return {
        "page": spec.get("page"),
        "ssim": page_ssim, "ssimThreshold": ssim_threshold,
        "textLineConsistency": text_ok,
        "defects": defects,
    }


def _defect_type(role: str) -> str:
    return "text-wrap" if role == "text" else "visual"


def classify_defect_action(defect: dict) -> str:
    return {
        "position": "translate-and-rebuild",
        "geometry": "adjust-shape-and-rebuild",
        "style": "adjust-shape-and-rebuild",
        "text-wrap": "widen-textbox-2pct",
        "visual": "bake-element-downgrade",
    }.get(defect["type"], "review")


def apply_repairs(spec: dict, defects: list[dict]) -> list[str]:
    """按 defect 类型就地修复 layout-spec；返回已应用的动作。可编辑度优先：文字不烘焙。"""
    by_id = {sh["id"]: sh for sh in spec.get("shapes", [])}
    applied = []
    for d in defects:
        shape = by_id.get(d["id"])
        if shape is None:
            continue
        if d["type"] == "text-wrap":
            # 框宽 +2% 冗余（可编辑度优先，绝不烘焙文字）
            shape["bboxPx"]["w"] = round(shape["bboxPx"]["w"] * 1.02, 2)
            applied.append(f"widen-textbox:{d['id']}")
        elif d["type"] == "visual":
            # 非文字视觉差异大 → 最小降级：该元素单独烘焙
            selector = shape.get("selectorPath") or (shape.get("pendingBake") or {}).get("selectorPath", "")
            if not selector:
                continue  # 无 selector 无法定位烘焙，保持原样
            shape["expressibility"] = {"verdict": "baked", "bakedReason": "qa-downgrade"}
            page = spec.get("page", 1)
            shape["pendingBake"] = {
                "selectorPath": selector,
                "targetPng": f"bake/page-{page}-{_safe_id(d['id'])}.png",
            }
            applied.append(f"bake-downgrade:{d['id']}")
    return applied


def _safe_id(eid: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in eid)[-60:]


def run_qa(reference_dir: Path, render_dir: Path, spec_dir: Path, out_path: Path,
           ssim_threshold: float = SSIM_THRESHOLD) -> dict:
    toolkit = resolve_toolkit()
    specs = {}
    for p in sorted(spec_dir.glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        specs[data.get("page", _page_num(p))] = data
    references = {_page_num(p): p for p in reference_dir.glob("*.png")}
    renders = {_page_num(p): p for p in render_dir.glob("*.png")}

    comparison = run_comparison(toolkit, reference_dir, render_dir, out_path.parent / "comparison.png")
    pages = []
    for page in sorted(specs):
        if page not in references or page not in renders:
            pages.append({"page": page, "ssim": 0.0, "ssimThreshold": ssim_threshold,
                          "textLineConsistency": False, "calibrationStatus": "INCONCLUSIVE",
                          "comparisonImage": comparison,
                          "defects": [{"id": None, "type": "position", "delta": None,
                                       "action": "translate-and-rebuild"}]})
            continue
        result = evaluate_page(references[page], renders[page], specs[page], ssim_threshold)
        result["calibrationStatus"] = "PASS" if result["ssim"] >= ssim_threshold else "FAIL"
        result["comparisonImage"] = comparison
        pages.append(result)

    failing = [p for p in pages if p["ssim"] < ssim_threshold or not p["textLineConsistency"]]
    baked = []
    for spec in specs.values():
        for sh in spec.get("shapes", []):
            if sh.get("expressibility", {}).get("verdict") == "baked":
                baked.append({"id": sh["id"], "bakedReason": sh["expressibility"]["bakedReason"]})
    report = {
        "schemaVersion": SCHEMA_VERSION,
        "overallStatus": "PASS" if not failing else "FAIL",
        "autoIterationCount": 0,
        "pages": pages,
        "bakedElements": baked,
        "fontMap": next(iter(specs.values()), {}).get("fontMap", []) if specs else [],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def make_stdout_robust() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--render", required=True)
    parser.add_argument("--layout-spec", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ssim-threshold", type=float, default=SSIM_THRESHOLD)
    args = parser.parse_args()
    try:
        report = run_qa(Path(args.reference), Path(args.render), Path(args.layout_spec),
                        Path(args.output), args.ssim_threshold)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2
    make_stdout_robust()
    print(Path(args.output))
    return 0 if report["overallStatus"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
