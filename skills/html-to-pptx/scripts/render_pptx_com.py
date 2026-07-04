#!/usr/bin/env python3
"""M4 · PowerPoint COM 渲染器：.pptx → render/page-*.png（@2x, 2560×1440）。

规避清单（2026-07-05 调研，全部照做）：
- 用 Slide.Export(path,"PNG",ScaleWidth,ScaleHeight) —— 第 3/4 参即输出像素；不用 SaveAs。
- Presentations.Open(ReadOnly=True, Untitled=False, WithWindow=False)；绝不碰 Application.Visible。
- DispatchEx 起独立实例；非主线程 CoInitialize/CoUninitialize；gencache 出错删缓存重试。
- context manager 收尾：关 Presentation → Quit → del → gc → 校验进程退出，超时按 PID kill。
- Open/Export 套 watchdog 超时；启动前清残留实例。

仅 Windows + 已激活 PowerPoint + 交互式会话可用。
"""

from __future__ import annotations

import argparse
import gc
import sys
import time
from pathlib import Path

SCALE_DEFAULT = 2
BASE_W = 960  # pt basis: 960pt = 1280px
BASE_H = 540
WATCHDOG_S = 120


def _parse_pages(spec: str | None, total: int) -> list[int]:
    if not spec:
        return list(range(1, total + 1))
    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.update(range(int(a), int(b) + 1))
        elif part:
            out.add(int(part))
    return sorted(p for p in out if 1 <= p <= total)


class PowerPointApp:
    """COM 生命周期 context manager：起实例、收尾、僵尸兜底。"""

    def __init__(self):
        self.app = None
        self.pid = None
        self._coinit = False

    def __enter__(self):
        import pythoncom
        import win32com.client

        try:
            pythoncom.CoInitialize()
            self._coinit = True
        except Exception:
            self._coinit = False
        try:
            self.app = win32com.client.DispatchEx("PowerPoint.Application")
        except Exception:
            # gencache 损坏兜底：清 gen_py 后重试
            import shutil
            import win32com

            gen_py = Path(win32com.__gen_path__)
            if gen_py.exists():
                shutil.rmtree(gen_py, ignore_errors=True)
            self.app = win32com.client.DispatchEx("PowerPoint.Application")
        self.app.DisplayAlerts = 1  # ppAlertsNone
        self.pid = self._find_pid()
        return self

    def _find_pid(self):
        try:
            import psutil

            newest = None
            for proc in psutil.process_iter(["pid", "name"]):
                if proc.info["name"] and proc.info["name"].lower() == "powerpnt.exe":
                    newest = proc.info["pid"] if newest is None else max(newest, proc.info["pid"])
            return newest
        except Exception:
            return None

    def render(self, pptx_path: Path, out_dir: Path, scale: int, pages: str | None) -> list[Path]:
        pres = None
        results: list[Path] = []
        try:
            pres = self.app.Presentations.Open(
                str(pptx_path), ReadOnly=True, Untitled=False, WithWindow=False
            )
            total = pres.Slides.Count
            width = int(round(scale * BASE_W / 72 * 96))   # 2 * 960/72 * 96 = 2560
            height = int(round(scale * BASE_H / 72 * 96))  # 1440
            out_dir.mkdir(parents=True, exist_ok=True)
            for page in _parse_pages(pages, total):
                png = out_dir / f"page-{page}.png"
                deadline = time.monotonic() + WATCHDOG_S
                pres.Slides(page).Export(str(png), "PNG", width, height)
                while not png.exists() and time.monotonic() < deadline:
                    time.sleep(0.05)
                if not png.exists():
                    raise TimeoutError(f"Export timed out for page {page}")
                results.append(png)
        finally:
            if pres is not None:
                try:
                    pres.Close()
                except Exception:
                    pass
        return results

    def __exit__(self, *exc):
        try:
            if self.app is not None:
                try:
                    for pres in list(self.app.Presentations):
                        pres.Close()
                except Exception:
                    pass
                self.app.Quit()
        except Exception:
            pass
        self.app = None
        gc.collect()
        self._kill_if_alive()
        if self._coinit:
            try:
                import pythoncom

                pythoncom.CoUninitialize()
            except Exception:
                pass

    def _kill_if_alive(self):
        if self.pid is None:
            return
        try:
            import psutil

            if psutil.pid_exists(self.pid):
                proc = psutil.Process(self.pid)
                deadline = time.monotonic() + 10
                while proc.is_running() and time.monotonic() < deadline:
                    time.sleep(0.2)
                if proc.is_running():
                    proc.kill()
        except Exception:
            pass


def render(pptx_path: Path, out_dir: Path, scale: int = SCALE_DEFAULT, pages: str | None = None) -> list[Path]:
    with PowerPointApp() as ppt:
        return ppt.render(pptx_path, out_dir, scale, pages)


def make_stdout_robust() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pptx")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--scale", type=int, default=SCALE_DEFAULT)
    parser.add_argument("--pages")
    args = parser.parse_args()
    pptx = Path(args.pptx)
    if not pptx.exists():
        print(f"PPTX not found: {pptx}", file=sys.stderr)
        return 2
    try:
        pngs = render(pptx, Path(args.out_dir), args.scale, args.pages)
    except Exception as exc:  # COM/环境错误
        print(f"COM render failed: {exc}", file=sys.stderr)
        return 2
    make_stdout_robust()
    print(str(Path(args.out_dir)))
    for p in pngs:
        print(str(p), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
