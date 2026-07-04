# 全自动校准

用于 Mode B/C 的 AI 自主重构。参考图只作为临时校准表面，不进入最终可编辑稿。准确性来自可执行闭环：

`测量 -> 构建 -> 渲染 -> 计算偏移/字体误差 -> 返修 -> 验证证据`

## 必需产物

- `reference-measurements.json`：坐标变换、宏观锚点和 `anchorQuality`。
- 测量标注图与 reference/render 校准叠加图。
- `coordinate-calibration.json`：由 `calibrate_reference_render.py` 计算，不能手填 PASS。
- `typography-calibration.json`：由 `score_typography_candidates.py` 测量并选择候选。
- 参考图/渲染图对照、视觉还原度报告和最终 QA 报告。

## 坐标锁

1. 运行 `extract_reference_measurements.py`。默认 `--fit-mode auto`；比例不一致时使用 `contain` 并记录警告，禁止静默拉伸。
2. 仅使用 `anchorQuality.status = PASS` 的大面板、图片区、边框和稳定长线作为候选；不得用文字碎片或贯穿画布的噪声线凑足数量。
3. 构建并渲染 PPTX 后运行 `calibrate_reference_render.py`，计算每个锚点的 `dx`、`dy`、置信度和最大偏移。
4. 匹配数量不足时状态必须为 `INCONCLUSIVE`；偏移超过容差时为 `FAIL`；只有脚本证据满足门槛时才能为 `PASS`。
5. 最终对象坐标全部来自同一个 `coordinateTransform`。默认宏观容差为 `max(6 px, 画布长边的 0.5%)`。

## 形状策略

- `native-shape`：卡片、面板、标签、边框、规则线和简单渐变。
- `independent-image`：内容图片、截图和可替换素材。
- `baked-asset`：纹理、复杂光晕、雾气、不规则遮罩和照片边缘融合。
- `mode-b-fallback`：无法稳定分层、但允许在 Mode B 边界内烘焙的复杂区域。

轮廓置信度低于 `0.75` 时自动选择安全回退。只有对象必须独立编辑且没有稳定原生表达或允许回退时，才设置 `needsHumanReview`。

## 字体渲染探针

1. 每个主文字样式生成 2–4 个候选，包含字体、字号、字重、行距、文本框尺寸、内边距和垂直对齐。
2. 由 Presentations 运行时使用最终 `acceptanceRenderer` 生成候选 PNG。
3. 运行 `score_typography_candidates.py` 测量字形 bbox、行数、行间距、基线代理和裁切（`clippingDetected`）。
4. 行数不一致或发生裁切的候选直接淘汰；其余候选按渲染误差自动选择。禁止用 auto-shrink 代替校准。
5. 同一句多样式文字保持一个富文本框和独立 runs，以整句连续阅读区域统一评分。

### 字体候选种子（`target_font` 为空时）

`target_font` 未指定时，按参考图文字特征从下表选 2–3 个同类系统字体作为 `fontCandidateSet` 种子，再由渲染误差自动选优，不阻塞等待人工选字：

| 文字类别 | 无衬线（默认） | 衬线（参考图有明显衬脚时） |
| --- | --- | --- |
| 中文正文 | Microsoft YaHei、Source Han Sans SC（思源黑体）、PingFang SC | Source Han Serif SC（思源宋体）、SimSun（宋体） |
| 中文标题 | Microsoft YaHei（粗）、SimHei（黑体）、Source Han Sans SC Bold | Source Han Serif SC Bold、STZhongsong |
| 西文正文 | Arial、Helvetica、Calibri | Times New Roman、Georgia |
| 西文标题 | Arial Bold、Helvetica Neue、Montserrat | Georgia Bold、Playfair Display |

筛选规则:(1) 先按笔画有无衬脚定衬线/非衬线列;(2) 标题类按参考图字重就近取粗字重家族;(3) 中西文混排时中文与西文各取一套并在同一 run 内分别指定 eastAsian/latin。命中的家族缺失时回退到同类下一候选。

## 返修与降级

首次构建记为 `autoIterationCount = 0`；每次返修后递增，最多 3 次。每轮只修改失败区域，并重新渲染受影响页面。

三轮后仍失败时不得声明 Level 2/3 通过。按最小破坏原则将复杂视觉降级为 `baked-asset` 或 Mode B，保留承诺可编辑的文字和结构，并记录 `autoFallbacks` 与 `autoFidelityBlocked`。

## 最终验证

运行 `validate_rebuild_evidence.py`。它负责旧字段迁移、文件存在性、对象来源引用、计算证据和 QA 门禁；禁止用手填布尔值代替脚本证据。

`needsHumanReview` 仅用于业务关键文字存在多种合理读法、必须编辑的复杂对象无法稳定实现，或参考图裁切/页序/版式意图确实未知的情况。
