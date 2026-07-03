# Visual Extraction Pass

用于 Mode B/C 在制作 PPTX 前，把参考图拆成可执行的视觉参数。目标不是让机器一次完美识别图片，而是建立可验证的测量证据和自动回调闭环，避免凭印象写坐标、形状和字号。默认由 agent 自行完成校准；不要求用户逐页确认锚点。

## 产物

每页必须保存：

- `visual-extraction.json`：文字、形状、图片和间距清单。
- 测量标注图：参考图上叠加候选 bbox 和自动宏观锚点。
- `coordinate-calibration.json` 或测量结果中的 `coordinateTransform`：原图像素与 PPT 画布之间的唯一映射、锚点、误差和临时校准层路径。
- `typography-calibration.json`：字号、行距、文本框宽高和内边距的候选与最终选择。
- `layout-spec.json` 和 `style-spec.md`：由视觉抽取转写，不直接从空白模板猜参数。

可复制 [visual-extraction-template.json](../assets/templates/visual-extraction-template.json)、[typography-calibration-template.json](../assets/templates/typography-calibration-template.json) 和 [autonomous-calibration.md](autonomous-calibration.md)。

## 标准流程

1. 将参考图映射到 1280 x 720 坐标系；记录原始尺寸、缩放、偏移、裁切和 fit mode。每页只允许一个 `coordinateTransform` 作为源像素到 PPT 坐标的依据。
2. 运行 `scripts/extract_reference_measurements.py` 生成候选文本行、线条、区域框、主色、坐标变换、自动锚点和标注图；默认 `--fit-mode auto`，禁止非等比静默拉伸。
3. 生成临时校准层：用 3-12 个稳定自动宏观锚点覆盖主卡片、图片区、标题带、正文区或页脚。不得用文字碎片和贯穿画布的噪声线凑数；少于 3 个时设为 `INSUFFICIENT`。整页参考图只允许存在于该临时层。
4. 构建并渲染后运行 `scripts/calibrate_reference_render.py`，计算 anchor offset；`INCONCLUSIVE` 或 `FAIL` 都不能进入坐标 PASS。再合并同一文本块、删除噪声框并补充主要结构，不请求用户逐点确认。
5. 为每个页面对象分配稳定角色：`title-*`、`body-text-*`、`tag-*`、`body-panel-*`、`decor-line-*`、`content-image-*` 等。
6. 对文字对象填写 bbox、行数、颜色、估计字重、字体候选、候选字号、构建单位、渲染后 bbox 和校准结果。
7. 对形状对象填写类型、bbox、圆角、填充、描边、透明度、阴影、层级、可编辑策略、自动回退策略和置信度。
8. 对图片对象填写 bbox、裁切、是否可替换、是否可烘焙、允许覆盖它的标签/遮罩/装饰，以及与背景/文字的边缘关系。
9. 记录间距 token：页面边距、列宽、标题到副标题、标签到正文、正文框内边距、页码线到画布边缘。
10. 低置信对象不得静默进入 PPT 构建；自动选择 `native-shape`、`baked-asset` 或 `mode-b-fallback`。只有“必须独立编辑且无稳定实现”的对象才能设为 `needsHumanReview`。
11. 由 `visual-extraction` 生成 `layout-spec`；每个 `layout-spec.objects[]` 记录 `sourceExtractionId` 和 `coordinateCalibrationId`。

## 形状理解规则

优先使用 PPT 原生形状：

- `rect`：卡片、底板、色块、遮罩。
- `roundRect`：胶囊标签、圆角正文框、圆角卡片。
- `line`：分隔线、页码线、短装饰线。
- `freeform`：只有轮廓稳定、点数少、确实需要可编辑时使用。
- 原生渐变形状：仅用于规则、单向、无纹理过渡。

转为图片或资产：

- 有真实纹理、复杂光晕、雾气、颗粒、照片边缘羽化。
- 形状边界不规则且不能用少量原生点稳定表达。
- 需要与人物、背景或内容图自然融合。
- agent 连续两轮无法稳定判断形状类型、层级或边缘。

禁止：

- 用大量无名小矩形拼出一个本可用圆角矩形、线条或图片资产表达的元素。
- 用透明窄条掩盖裁切错误、底色错误或过渡失败。
- 对低置信形状直接写成确定的原生对象。
- 把坐标映射、锚点叠加和渲染回看交给用户逐项判断，而不记录自动校准证据。

允许的覆盖必须显式记录：如果标签、遮罩、角标或装饰形状按参考图覆盖图片，且不影响文字可读性，在 shape 的 `overlapPolicy` 或 image 的 `allowedOverlays` 中说明。该情况不计入 `visualOverlapCount`，但如果位置、层级或裁切明显偏离参考图，仍按视觉还原度问题处理。

## 字号和间距校准

不要从参考图直接认定一个字号。使用候选校准：

1. 从参考图记录文字块 bbox、实际字形 bbox、行数、行距像素、文本框内边距和换行位置。
2. 用目标字体或自动 `fontCandidateSet` 与真实文案生成 2-4 个候选；优先偶数 pt，但允许记录例外。
3. 对每个候选组合记录：`fontFamily`、`fontSizePt`、构建 API 单位、`lineSpacingPercent`、`textBoxW/H`、`marginLeft/Top/Right/Bottom`、渲染后文本块 bbox、基线差和换行结果。
4. 用 `scripts/score_typography_candidates.py` 测量候选 PNG 并选择最低有效误差；若参考图伪字导致字宽不可比，以字高、行距、基线和整体文本块高度为主。
5. 修复后必须在同一 `acceptance_renderer` 重新渲染并更新校准记录；不得沿用旧截图判断文字大小。

经验起点：

- 在 1280 x 720 渲染坐标下，参考图中字形高度只能作为候选范围，不是最终 pt。
- 中文或 CJK 字体通常应以整段文本块高度、行距和留白校准，不只看单字高度。
- 标题优先校准视觉重量、换行和基线；正文优先校准可读性、行距、段落高度和框内留白。
- 标签优先校准胶囊高度、左右内边距和单行居中。

## 通过条件

Mode B/C 构建前必须满足：

- 每页 `visual-extraction` 已落盘。
- `coordinateTransform`、自动锚点、临时校准层和叠加误差已落盘，且 `coordinateCalibration.status = PASS`。
- 每个最终可编辑对象有 `sourceExtractionId` 或来源说明。
- 每个文字样式有 typography calibration 记录。
- 低置信形状、文字或图片对象已进入风险列表并闭环。
- `layout-spec` 的坐标、字号、间距来自视觉抽取或明确的跨页风格复用，而不是空白模板猜值。
