---
name: html-to-pptx
description: Use when converting fixed-ratio AI-generated HTML slides (or HTML fragments) into highly-editable, high-fidelity PPTX deliverables.
---

# HTML to PPTX

把 AI 生成的固定比例 HTML 页面转成 PPTX,三个硬目标:**超高还原度**(浏览器渲染 ≈ PPTX 渲染,QA 双门禁)、**超高可编辑度**(文字=原生文本框、形状=原生 autoshape、图片=独立对象,仅不可表达元素才烘焙)、**干净整洁**(无冗余 wrapper、同 bounds 合并、语义分组、z-order 正确)。

## Start Here

一条命令跑完整流水线(提取 → 变换 → 烘焙 → 构建 → COM 渲染 → QA → 自动返修):

```powershell
python scripts/run_pipeline.py --html <file|dir> --out-dir out
```

- 无 PowerPoint 时只跑离线子集:`--steps extract,transform,build`(产出 `out/deck.pptx`,跳过渲染/QA)。
- 产物:`out/deck.pptx`、`out/qa-report.json`、`out/comparison.png`、`out/pipeline-report.json`。

## 核心原则

- **坐标系全程唯一**:1280×720 CSS px = 960×540 pt = 标准 16:9(12192000×6858000 EMU);`px × 9525 = EMU`。DPR=2 只影响截图位图,DOM 几何一律 CSS px。
- **测最终盒子,不管布局语义**:几何来自浏览器 `getBoundingClientRect` / `Range.getClientRects`,不解析 flex/grid/绝对定位。
- **可编辑度优先**:文字**绝不烘焙**;返修时文字只加宽框/微调字号,非文字元素视觉差异大才最小降级为烘焙 PNG(记 `bakedReason`)。
- **仅 16:9**(沿用 ppt-rebuild 决策口径):非 16:9 输入声明降级——走整页图或经确认后等比映射进 1280×720,不做扩展坐标规范。

## 输入约定

- 输入为 AI 生成的**固定比例** HTML:单文件按整页高度逐屏切 720px 为多页(`--paginate fixed`,默认),或一目录一文件一页(`natural_key` 排序)。
- 字体、图片等资源需可离线加载(`file://`)或已内联;跨域字体会静默降级,提取前已 `document.fonts.ready`。

## 烘焙策略(可表达性评分)

- **原生**:纯色/线性渐变(≤8 stops)/中心对称径向、四角圆角、单层 outer shadow、实/虚线边框、透明度、图片、表格单元格文字。
- **必须烘焙**:`backdrop-filter`、`clip-path`、`mask`、`mix-blend-mode≠normal`、多层/inset 阴影、conic-gradient、canvas/video、复杂 SVG。默认简单 SVG 也烘焙,`--svg-as-shapes` 试原生 freeform(风险自担)。
- 每个烘焙判定带 `bakedReason` 进最终报告,供可编辑度审计。

## QA 与失败降级

- 双门禁:全页 SSIM ≥ 阈值(默认 0.93)+ 逐元素 SSIM/颜色差 + 文字折行一致性(渲染行数 vs `textLayoutBudget`)。
- 自动返修 ≤3 轮(首建记第 0 轮):文字折行 → 框宽 +2%;非文字视觉差异 → 最小降级烘焙。
- 3 轮后仍不过 → 交付但 `overallStatus: "PARTIAL"`,`defects` 全量列出。

## 环境前置

- **PowerPoint(Office16)已激活**、**交互式会话**(非 service/Session 0);COM 渲染用 `Slide.Export` 输出 2560×1440 PNG,进程收尾有 psutil 兜底。
- Playwright chromium 已安装(`playwright install chromium`);python-pptx、pywin32、numpy/scipy、Pillow。
- QA 工具默认路径复用同级 `../ppt-rebuild-workflow/scripts`;`HTML2PPTX_QA_TOOLKIT` 可覆盖。

## 脚本

- `scripts/extract_html.py`:Playwright 提取几何/样式/文字/截图 → `extraction/*.json` + `reference/*.png`。
- `scripts/build_layout_spec.py`:角色分类/扁平化整洁/可表达性评分 → `layout-spec.json`。
- `scripts/build_pptx.py`:layout-spec → `.pptx`(原生对象 + 烘焙占位)。
- `scripts/render_pptx_com.py`:PowerPoint COM 导出 `render/*.png`(@2x)。
- `scripts/qa_gate.py`:双门禁 + 返修策略 → `qa-report.json`。
- `scripts/run_pipeline.py`:一键驱动 + 返修循环 → `pipeline-report.json`。

字段契约与 CLI/退出码见 [pipeline-contracts.md](references/pipeline-contracts.md)。
