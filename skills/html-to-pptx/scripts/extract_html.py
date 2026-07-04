#!/usr/bin/env python3
"""M1 · Playwright 提取器：HTML → reference PNG(@2x) + extraction.json（几何/样式/文字）。

坐标全为 CSS px（1280×720）。DPR=2 只影响截图位图。见 references/pipeline-contracts.md。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

VIEWPORT_W = 1280
VIEWPORT_H = 720
DPR = 2
SCHEMA_VERSION = "1.0"

EXTRACTOR_JS = (Path(__file__).resolve().parent / "extractor.js").read_text(encoding="utf-8")

IMAGE_HTML_EXT = {".html", ".htm"}


def natural_key(path: Path) -> list:
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", path.name)]


def make_stdout_robust() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")


def html_inputs(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(
            [p for p in path.iterdir() if p.suffix.lower() in IMAGE_HTML_EXT],
            key=natural_key,
        )
    return []


def _fit_document_pages(page) -> int:
    """fixed 分页：文档总高 → 页数（每页 720 CSS px）。"""
    height = page.evaluate(
        "() => Math.max(document.documentElement.scrollHeight, document.body ? document.body.scrollHeight : 0)"
    )
    return max(1, -(-int(height) // VIEWPORT_H))  # ceil


def extract_file(page, html_path: Path, paginate: str) -> list[dict]:
    """返回该文件的逐页 extraction dict（未写盘）。"""
    page.goto(html_path.resolve().as_uri(), wait_until="load")
    page.evaluate("async () => { if (document.fonts) { await document.fonts.ready; } }")

    if paginate == "fixed" and page.viewport_size and html_path.is_file():
        page_count = _fit_document_pages(page)
    else:
        page_count = 1

    results = []
    for index in range(page_count):
        clip_top = index * VIEWPORT_H
        data = page.evaluate(EXTRACTOR_JS, {"clipTop": clip_top, "clipHeight": VIEWPORT_H})
        results.append(
            {
                "schemaVersion": SCHEMA_VERSION,
                "source": str(html_path),
                "viewport": {"width": VIEWPORT_W, "height": VIEWPORT_H, "dpr": DPR},
                "coordinateSystem": {"unit": "csspx", "width": VIEWPORT_W, "height": VIEWPORT_H},
                "clipTop": clip_top,
                "elements": data["elements"],
            }
        )
    return results


def screenshot_page(page, out_png: Path, clip_top: int) -> None:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(
        path=str(out_png),
        clip={"x": 0, "y": clip_top, "width": VIEWPORT_W, "height": VIEWPORT_H},
    )


def run(html: Path, out_dir: Path, paginate: str) -> dict:
    from playwright.sync_api import sync_playwright

    inputs = html_inputs(html)
    if not inputs:
        raise SystemExit(f"No HTML inputs found: {html}")

    extraction_dir = out_dir / "extraction"
    reference_dir = out_dir / "reference"
    extraction_dir.mkdir(parents=True, exist_ok=True)
    reference_dir.mkdir(parents=True, exist_ok=True)

    pages_manifest = []
    page_number = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(
            viewport={"width": VIEWPORT_W, "height": VIEWPORT_H}, device_scale_factor=DPR
        )
        page = context.new_page()
        try:
            for html_path in inputs:
                per_file = extract_file(page, html_path, paginate)
                for local_index, data in enumerate(per_file):
                    page_number += 1
                    data["page"] = page_number
                    ref_rel = f"reference/page-{page_number}.png"
                    data["reference"] = ref_rel
                    screenshot_page(page, out_dir / ref_rel, data.pop("clipTop"))
                    json_path = extraction_dir / f"page-{page_number}.json"
                    json_path.write_text(
                        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    pages_manifest.append(
                        {
                            "page": page_number,
                            "source": str(html_path),
                            "extraction": str(json_path),
                            "reference": str(out_dir / ref_rel),
                            "elementCount": len(data["elements"]),
                        }
                    )
        finally:
            context.close()
            browser.close()
    return {"outDir": str(out_dir), "pages": pages_manifest}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", required=True, help="HTML file or directory")
    parser.add_argument("--paginate", choices=("fixed", "single"), default="fixed")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--json", action="store_true", help="Print page manifest to stdout")
    args = parser.parse_args()

    html = Path(args.html)
    if not html.exists():
        print(f"HTML input not found: {html}", file=sys.stderr)
        return 2
    out_dir = Path(args.out_dir)
    try:
        manifest = run(html, out_dir, args.paginate)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    make_stdout_robust()
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False))
    else:
        print(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
