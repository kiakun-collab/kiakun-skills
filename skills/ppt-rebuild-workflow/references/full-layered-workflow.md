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
5. 参考 `assets/templates/layout-spec-mode-c-example.json` 建立 `layout-spec.json`，使用 1280 x 720 坐标系。
6. 建立 `style-spec.md`，记录每类文字和结构样式。
7. 生成纯背景候选和人物透明 PNG，或说明核心视觉不可拆分的例外。
8. 构建 PPTX。
9. 重导入或渲染为 PNG。
10. 生成参考图与渲染图的整页并排图；分别执行文字可读性和视觉还原度双门禁，不使用多轮裁剪恢复 AI 伪字或判断整体构图。
11. 检查分层后的版式、构图、层级、色彩、字体观感、间距和关键素材是否达到参考图目标。
12. 完成 `assets/templates/level-3-delivery-checklist.md`，执行 Level 3 QA 并返修。

## 硬门槛

- `wholeReferenceImageEmbedded = false`
- `combinedBackgroundPersonPictureCount = 0`，除非 asset-audit 明确说明不可拆分例外。
- `contentPicturesAreIndependentObjects = true`
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
