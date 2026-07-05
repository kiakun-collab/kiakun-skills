# html-to-pptx · 管线契约

> 四个 JSON 产物 + 各脚本 CLI/退出码的**唯一事实源**。字段一经定稿只增不改不删（全局规约 4）。
> 坐标系全程唯一：CSS px（1280×720），`emuPerPx = 0.75 × 12700 = 9525`。DPR=2 只影响位图，与截图像素比较时才 ×2。

## 通用 CLI 约定

- stdout 只打印最终产物路径；进度/警告走 stderr；`--json` 可选打印摘要。
- 输出 `encoding="utf-8"` + `ensure_ascii=False`；stdout 打印前 `reconfigure(errors="backslashreplace")`。
- 退出码：`0` 成功 / `1` 门禁 FAIL（QA 未过） / `2` 输入或环境错误。

---

## 1. extraction.json（M1 产出，逐页一个）

```jsonc
{
  "schemaVersion": "1.0",
  "page": 1,
  "source": "<html 文件路径>",
  "viewport": { "width": 1280, "height": 720, "dpr": 2 },
  "reference": "reference/page-1.png",           // DPR=2 截图，2560×1440
  "coordinateSystem": { "unit": "csspx", "width": 1280, "height": 720 },
  "elements": [
    {
      "id": "html>body>div:nth-of-type(1)",       // 稳定 DOM 路径，贯穿全管线做 QA 溯源
      "tag": "div",
      "paintIndex": 0,                             // 实际绘制顺序（stacking context 解析后）
      "bbox": { "x": 0, "y": 0, "w": 1280, "h": 720 },        // getBoundingClientRect（post-transform AABB, CSS px）
      "untransformedBox": { "x": 0, "y": 0, "w": 0, "h": 0 },  // transform≠identity 时的未变换盒，否则 null
      "transform": {                               // null 表示 identity
        "matrix": [1, 0, 0, 1, 0, 0],
        "rot": 0.0,                                // 度
        "scaleX": 1.0, "scaleY": 1.0,
        "translateX": 0.0, "translateY": 0.0
      },
      "style": {
        "background": {
          "raw": "rgb(255, 255, 255)",
          "type": "color|linear-gradient|radial-gradient|image|none",
          "color": "#RRGGBBAA",                    // type=color 时
          "stops": [{ "color": "#RRGGBBAA", "offset": 0.0 }],  // 渐变时
          "angle": 90.0,                           // linear-gradient 时（度，CSS 语义）
          "imageUrl": "..."                        // type=image 时
        },
        "border": {
          "top":    { "width": 0, "color": "#RRGGBBAA", "style": "none" },
          "right":  { "width": 0, "color": "#RRGGBBAA", "style": "none" },
          "bottom": { "width": 0, "color": "#RRGGBBAA", "style": "none" },
          "left":   { "width": 0, "color": "#RRGGBBAA", "style": "none" },
          "radius": { "tl": 0, "tr": 0, "br": 0, "bl": 0 }
        },
        "boxShadow": [
          { "offsetX": 0, "offsetY": 4, "blur": 12, "spread": 0, "color": "#00000040", "inset": false }
        ],
        "opacity": 1.0,
        "overflow": "visible",
        "zIndex": "auto",                          // "auto" 或整数
        "mixBlendMode": "normal"
      },
      "text": {                                     // 无直接文字则 null
        "content": "Hello world",
        "lines": [                                  // Range.getClientRects 逐行矩形（CSS px）
          { "x": 10, "y": 10, "w": 120, "h": 24, "text": "Hello" }
        ],
        "font": {
          "family": "Inter, system-ui, sans-serif",
          "sizePx": 16, "weight": 400, "style": "normal",
          "lineHeightPx": 24, "letterSpacingPx": 0,
          "color": "#111111FF", "align": "left", "whiteSpace": "normal"
        }
      },
      "image": {                                    // 无则 null
        "kind": "img|background|svg|canvas",
        "naturalWidth": 0, "naturalHeight": 0,
        "currentSrc": "...",                        // img
        "svg": "<svg ...>...</svg>",                // svg outerHTML
        "dataUrl": "data:image/png;base64,...",     // canvas toDataURL（成功时）
        "tainted": false                            // canvas 跨域污染
      },
      "rasterize": {                                // 只记事实，M2 评分用
        "required": false,
        "reasons": ["backdrop-filter", "filter", "clip-path", "mask", "mix-blend-mode", "canvas", "video", "complex-svg"]
      },
      "selectorPath": "html > body > div:nth-of-type(1)"   // element_handle.screenshot() 定位用
    }
  ]
}
```

不可见元素（`display:none` / `visibility:hidden` / 零尺寸 / 视口外±容差）不进 `elements`。

---

## 2. layout-spec.json（M2 产出，逐页一个）

```jsonc
{
  "schemaVersion": "1.0",
  "page": 1,
  "mode": "html-to-pptx",
  "coordinateSystem": { "unit": "csspx", "width": 1280, "height": 720, "emuPerPx": 9525 },
  "reference": "reference/page-1.png",
  "cleanliness": { "emittedShapes": 0, "visibleElements": 0, "ratio": 0.0 },   // ratio>1.3 → warnings
  "fontMap": [
    { "source": "Inter, sans-serif", "target": "Segoe UI", "confidence": 0.9, "warning": null }
  ],
  "warnings": [],
  "shapes": [
    {
      "id": "html>body>div:nth-of-type(1)",   // = extraction 的 id
      "role": "text|shape|image|table|svg",
      "bboxPx": { "x": 0, "y": 0, "w": 0, "h": 0 },
      "rot": 0.0,
      "zOrder": 0,                              // = paintIndex
      "groupId": null,                          // 语义分组 → M3 出 PPT group
      "fill": {                                 // null=无填充
        "type": "solid|linear|radial",
        "color": "#RRGGBBAA",                   // solid
        "stops": [{ "color": "#RRGGBBAA", "offset": 0.0 }], "angle": 90.0   // gradient
      },
      "line": { "width": 1, "color": "#RRGGBBAA", "dash": "solid|dash|dot" },  // null=无边框
      "shadow": { "offsetX": 0, "offsetY": 4, "blur": 12, "color": "#00000040" }, // null
      "radius": { "tl": 0, "tr": 0, "br": 0, "bl": 0 },                          // null
      "text": {
        "runs": [{ "text": "Hi", "bold": false, "italic": false, "color": "#111111FF", "font": "Segoe UI", "sizePt": 12.0 }],
        "align": "left", "valign": "top",
        "lineBreaks": [],                        // 显式换行位置（pre/<br>）
        "paddingPx": { "top": 0, "right": 0, "bottom": 0, "left": 0 },
        "textLayoutBudget": { "lines": 1, "lineWidths": [120.0] }   // 折行一致性预算（M4 门禁用）
      },
      "image": { "src": "...", "objectFit": "cover", "srcRect": null },
      "table": { "rows": 0, "cols": 0, "colWidthsPx": [], "rowHeightsPx": [], "cells": [] },
      "expressibility": { "verdict": "native|baked", "bakedReason": null },
      "pendingBake": { "selectorPath": "...", "targetPng": "bake/page-1-<id>.png" }  // baked 时，否则 null
    }
  ],
  "groups": [{ "id": "g1", "children": ["id1", "id2"], "label": "card" }]
}
```

角色为 `structural` 的元素不进 `shapes`（只保留其子元素的 `groupId`）。

- `fontMap[].target` 是**本机真实注册字体名**（枚举 Windows 注册表 Fonts 键得到，PowerPoint 实际识别）。`confidence`:`1.0` 精确命中 / `0.9` 去空格大小写校正（如 `腾讯体W7`→`腾讯体 W7`）/ `0.8` web 字体映射 / `0.6` 通用族 / `0.5` 无匹配回退 Arial（有 fallback 风险，见 `warning`）。
- `warnings[]` 汇总:cleanliness ratio 超阈值、字体 fallback/校正、以及**超出 1280×720 画布**的元素（溢出/底部越界预警）。

---

## 3. qa-report.json（M4 产出，聚合一份）

```jsonc
{
  "schemaVersion": "1.0",
  "overallStatus": "PASS|PARTIAL|FAIL",
  "autoIterationCount": 0,                        // 0=首建，≤3
  "pages": [
    {
      "page": 1,
      "calibrationStatus": "PASS|INCONCLUSIVE|FAIL",
      "ssim": 0.95, "ssimThreshold": 0.93,
      "textLineConsistency": true,
      "comparisonImage": "qa/page-1-comparison.png",
      "defects": [
        { "id": "...", "type": "position|geometry|style|text-wrap|visual", "delta": 0.0, "action": "..." }
      ]
    }
  ],
  "bakedElements": [{ "id": "...", "bakedReason": "..." }],
  "fontMap": [],
  "outputPptx": "..."
}
```

## 4. pipeline-report.json（M5 run_pipeline 产出）

```jsonc
{
  "schemaVersion": "1.0",
  "status": "PASS|FAIL|EMPTY",
  "steps": [
    { "step": "extract|transform|build|render|qa", "status": "ok|nonzero|skipped", "exitCode": 0, "output": "...", "reason": null }
  ],
  "outputPptx": "...", "qaReport": "..."
}
```

---

## 脚本清单与 CLI

| 脚本 | 输入 | 输出 | 退出码 |
|---|---|---|---|
| `extract_html.py` | `--html <file\|dir> [--paginate fixed] --out-dir` | `reference/page-*.png` + `extraction/page-*.json` | 0/2 |
| `build_layout_spec.py` | `<extraction.json> --output [--svg-as-shapes]` | `layout-spec.json` | 0/2 |
| `build_pptx.py` | `<layout-spec.json ...> --output <pptx>` | `.pptx` + `pendingBake` 清单 | 0/2 |
| `render_pptx_com.py` | `<pptx> --out-dir [--scale 2] [--pages ...]` | `render/page-*.png` | 0/2 |
| `qa_gate.py` | `--reference <dir> --render <dir> --layout-spec <dir> --output` | `qa-report.json` | 0/1/2 |
| `run_pipeline.py` | `--html <file\|dir> --out-dir [--steps ...] [--stop-on-fail]` | `pipeline-report.json` + `.pptx` | 0/1/2 |

QA 工具（calibrate/comparison）按 D4 解析：默认 `../ppt-rebuild-workflow/scripts`，环境变量 `HTML2PPTX_QA_TOOLKIT` 可覆盖，找不到时退出码 2 并提示。
