#!/usr/bin/env python3
"""M5 · 一键驱动：HTML → PPTX（extract → transform → bake → build → render → qa → 返修）。

返修循环需要跨轮改 spec 并重建，故用**进程内编排**（不是纯 subprocess）；render/qa 依赖
PowerPoint COM，用 `--steps` 可只跑离线子集。产出 pipeline-report.json。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import build_layout_spec
import build_pptx
import extract_html
import qa_gate

ALL_STEPS = ("extract", "transform", "build", "render", "qa")
MAX_ITER = 3
DPR = 2


def _bake(items: list[dict], out_dir: Path) -> None:
    """按 selectorPath 用 Playwright 逐元素 @2x 截图，写 targetPng（绝对路径回填到 spec）。"""
    if not items:
        return
    from playwright.sync_api import sync_playwright

    by_source: dict[str, list[dict]] = {}
    for it in items:
        by_source.setdefault(it["source"], []).append(it)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1280, "height": 720}, device_scale_factor=DPR
        )
        page = context.new_page()
        try:
            for source, group in by_source.items():
                page.goto(Path(source).resolve().as_uri(), wait_until="load")
                page.evaluate("async () => { if (document.fonts) await document.fonts.ready; }")
                for it in group:
                    target = out_dir / it["targetPng"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    handle = page.query_selector(it["selectorPath"])
                    if handle is None:
                        continue
                    try:
                        handle.screenshot(path=str(target))
                        it["shape"]["image"] = {"src": str(target.resolve()), "objectFit": "fill", "srcRect": None}
                        it["shape"]["_baked"] = True
                    except Exception:
                        continue
        finally:
            context.close()
            browser.close()


def _collect_pending(specs: dict[int, dict], sources: dict[int, str]) -> list[dict]:
    items = []
    for page, spec in specs.items():
        for sh in spec["shapes"]:
            if sh.get("_baked"):
                continue  # 本次运行已烘焙
            if sh.get("expressibility", {}).get("verdict") == "baked" and sh.get("pendingBake"):
                selector = sh["pendingBake"].get("selectorPath") or ""
                if not selector.strip():
                    continue  # 无 selector 跳过烘焙（保留占位）
                items.append({"source": sources[page], "selectorPath": selector,
                              "targetPng": sh["pendingBake"]["targetPng"], "shape": sh})
    return items


def _write_specs(specs: dict[int, dict], spec_dir: Path) -> list[Path]:
    spec_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for page, spec in sorted(specs.items()):
        p = spec_dir / f"page-{page}.json"
        p.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
        paths.append(p)
    return paths


def run(html: Path, out_dir: Path, steps=None, stop_on_fail=False,
        max_iter=MAX_ITER, scale=DPR, ssim_threshold=qa_gate.SSIM_THRESHOLD) -> dict:
    steps = set(steps) if steps else set(ALL_STEPS)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_steps = []

    def record(step, status, output=None, reason=None):
        report_steps.append({"step": step, "status": status, "output": output, "reason": reason})

    # 1) extract
    manifest = extract_html.run(html, out_dir, "fixed")
    sources = {m["page"]: m["source"] for m in manifest["pages"]}
    record("extract", "ok", str(out_dir / "extraction"))

    # 2) transform
    specs: dict[int, dict] = {}
    for m in manifest["pages"]:
        extraction = json.loads(Path(m["extraction"]).read_text(encoding="utf-8"))
        specs[m["page"]] = build_layout_spec.transform(extraction)
    spec_dir = out_dir / "spec"
    _write_specs(specs, spec_dir)
    record("transform", "ok", str(spec_dir))

    if "build" not in steps:
        return _finish(out_dir, report_steps, None, None, "EMPTY")

    # 3) 初始 bake + build
    _bake(_collect_pending(specs, sources), out_dir)
    spec_paths = _write_specs(specs, spec_dir)
    pptx = out_dir / "deck.pptx"
    build_pptx.build(spec_paths, pptx)
    record("build", "ok", str(pptx))

    if not {"render", "qa"} <= steps:
        return _finish(out_dir, report_steps, str(pptx), None, "PASS")

    report = None
    iteration = 0
    while True:
        try:
            import render_pptx_com

            render_pptx_com.render(pptx, out_dir / "render", scale)
        except Exception as exc:
            record("render", "nonzero", reason=str(exc))
            if stop_on_fail:
                return _finish(out_dir, report_steps, str(pptx), None, "FAIL")
            break
        record("render", "ok", str(out_dir / "render"))
        report = qa_gate.run_qa(out_dir / "reference", out_dir / "render", spec_dir,
                                out_dir / "qa-report.json", ssim_threshold)
        report["autoIterationCount"] = iteration
        record("qa", "ok" if report["overallStatus"] == "PASS" else "nonzero", str(out_dir / "qa-report.json"))
        if report["overallStatus"] == "PASS" or iteration >= max_iter:
            break
        iteration += 1
        for page_report in report["pages"]:
            qa_gate.apply_repairs(specs.get(page_report["page"], {}), page_report.get("defects", []))
        _bake(_collect_pending(specs, sources), out_dir)
        spec_paths = _write_specs(specs, spec_dir)
        build_pptx.build(spec_paths, pptx)

    if report is not None and report["overallStatus"] != "PASS":
        report["overallStatus"] = "PARTIAL"
        (out_dir / "qa-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    status = report["overallStatus"] if report else "FAIL"
    return _finish(out_dir, report_steps, str(pptx),
                   str(out_dir / "qa-report.json") if report else None, status)


def _finish(out_dir, steps, pptx, qa_report, status) -> dict:
    result = {"schemaVersion": "1.0", "status": status, "steps": steps,
              "outputPptx": pptx, "qaReport": qa_report}
    (out_dir / "pipeline-report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def make_stdout_robust() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--steps", help="Comma subset of: " + ",".join(ALL_STEPS))
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--max-iter", type=int, default=MAX_ITER)
    parser.add_argument("--scale", type=int, default=DPR)
    args = parser.parse_args()
    html = Path(args.html)
    if not html.exists():
        print(f"HTML input not found: {html}", file=sys.stderr)
        return 2
    steps = args.steps.split(",") if args.steps else None
    result = run(html, Path(args.out_dir), steps, args.stop_on_fail, args.max_iter, args.scale)
    make_stdout_robust()
    print(str(Path(args.out_dir) / "pipeline-report.json"))
    return 0 if result["status"] in ("PASS", "EMPTY") else 1


if __name__ == "__main__":
    raise SystemExit(main())
