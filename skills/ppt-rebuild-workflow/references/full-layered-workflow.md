# Full Layered Workflow

用于高还原、正式交付、长期可编辑的 PPT 重构。

## 分层目标

- 页面底色：PPT background fill。
- 纯背景：独立图片，只含环境。
- 人物：透明 PNG，优先每个人独立。
- 内容图：每张截图、证据图、作品图独立图片对象。
- 文字：PPT 文本框或富文本 runs。
- 结构：PPT 原生形状。

## 标准流程

1. 冻结页码、参考图、原 PPTX、输出路径和不可覆盖文件。
2. 做页面语义拆解。
3. 从原 PPTX 提取文字、图片、关系 ID、坐标和层级线索。
4. 建立 `asset-audit`，区分直接复用、仅作身份参考、禁用、需要重生。
5. 运行 `scripts/extract_reference_measurements.py`，逐页保存 `reference-measurements.json`、坐标变换、自动锚点和测量标注图；在任何 `layout-spec` 创建前按 [autonomous-calibration.md](autonomous-calibration.md) 生成并验证临时校准层。
6. 按 [visual-extraction-pass.md](visual-extraction-pass.md) 把自动校准后的测量结果写入逐页 `visual-extraction`，明确每个文字、形状、人物、内容图和背景区域的 `x/y/w/h`、层级、置信度、测量证据和自动回退策略。
7. 建立 `typography-calibration`，用同一最终渲染后端的 2-4 个候选校准字体、字号、行距、文本框宽高和内边距。
8. 参考 `assets/templates/layout-spec-mode-c-example.json` 建立 `layout-spec.json`，使用 1280 x 720 坐标系，并让每个对象追溯到 `sourceExtractionId`、`coordinateCalibrationId`、原 PPTX 对象或资产审计项；禁止先写 `layout-spec` 再补测量记录。
9. 建立 `style-spec.md`，记录每类文字和结构样式、参考 bbox、渲染后 bbox 与校准证据。
10. 生成纯背景候选和人物透明 PNG；无法稳定分离的复杂区域自动转入 `baked-asset` 或 Mode B 回退，并说明例外。
11. 构建 PPTX。
12. 用接受渲染后端重导入或渲染为 PNG。
13. 生成参考图与渲染图的整页并排图；分别执行文字可读性和分区视觉还原度双门禁，不使用多轮裁剪恢复 AI 伪字或判断整体构图。
14. 自动返修受影响区域最多三轮，再检查分层后的版式、构图、层级、色彩、字体观感、间距和关键素材是否达到参考图目标。
15. 完成 `assets/templates/level-3-delivery-checklist.md`，执行 Level 3 QA；无法自动达到门槛时记录 `autoFidelityBlocked`，不得声称通过。

## 硬门槛

- `wholeReferenceImageEmbedded = false`
- `combinedBackgroundPersonPictureCount = 0`，除非 asset-audit 明确说明不可拆分例外。
- `contentPicturesAreIndependentObjects = true`
- 每个可编辑文字和结构形状有视觉抽取来源；低置信形状不得无说明进入最终 PPTX。
- typography calibration 已覆盖标题、正文、标签和页码等主要文字样式。
- `coordinateCalibration.status = PASS`，临时校准层已验证，最终 deck 不包含该参考层。
- 每个低置信且要求可编辑的对象都有稳定原生实现，或已按用户可编辑边界自动降级；未解决冲突为零。
- `unexpectedTextOverlapCount = 0`
- `forbiddenOverlayShapesDetected = 0`
- `visualFidelityStatus = PASS`
- `majorFidelityDeviationCount = 0`

每项必须在 QA 报告中记录 `automatedEvidence`、`manualEvidence` 和 `status`，不能使用无来源布尔值。

## 禁止事项

- 不把文字、标签、卡片和整页排版烘焙到背景图。
- 不用旧 PPTX 大背景直接充当最终背景，除非 asset-audit 证明构图完全吻合。
- 不用多层透明形状模拟雾气、光晕、渐隐、全页调色。
- 不凭感觉统一卡片尺寸和间距。
