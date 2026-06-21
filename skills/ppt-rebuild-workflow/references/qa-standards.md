# QA Standards

## Level 1 快览 QA

用于 Mode A。

- `slideCount` 正确。
- `mediaCount` 与页数匹配或可解释。
- `emptyMediaCount = 0`。
- 页序正确。
- 输出 contact sheet。

## Level 2 半可编辑 QA

用于 Mode B。Level 1 全部通过，并完成以下自动审计和视觉门禁。

### Level 2 必须自动审计

- 按 [text-recovery.md](text-recovery.md) 核对准确文案；AI 图像中的错字、乱码和伪字采用有来源的语义重建，不得通过裁剪或放大恢复。
- `textRecovery.unresolvedItems` 必须为空；否则设置 `needsHumanReview = true`，未经确认不能把内容准确性标记为通过。
- 运行 `scripts/audit_pptx_structure.py`。
- 分别检查 `latinFonts`、`eastAsianFonts`、`complexScriptFonts`、`symbolFonts` 和 `themeFonts`。
- `unresolvedInheritedFonts` 必须为空，或逐项给出人工验证和字体来源；不能把未解析继承当成通过。
- 文本运行存在，不能全部烘焙进图片。
- `fullSlideImageRiskPages` 为空；若非空，必须证明大图不是整页参考图或判定失败。
- `wholeReferenceImageEmbedded` 必须有自动风险证据及人工对照结论，不能写无来源的 `false`。
- 文本 `p:sp`、普通 shape、`p:pic` 分类型统计，`unknownRoleNames` 为 0 或逐项解释。
- 运行 `scripts/audit_pptx_text_frames.py`。
- `textFrameIntersections = 0`。
- 细长形状与文本框相交候选为 `0`，或逐项证明属于安全布局。
- `unresolvedTextFrameCount = 0`。
- `unresolvedGroupTransformCount = 0`；例外必须进入 `geometryCoverageRisks` 并人工复核。
- 普通分隔页每页长正文文本框候选默认恰好为 `1`；例外必须说明。
- 运行 `scripts/make_reference_render_comparison.py` 或等价流程；页码映射、缺失页、重复页和多余页检查通过，并保留 pairing JSON。
- 任务输入文件和每页 `layout-spec` 已落盘；关键渐隐、光晕和图片边缘已记录在 `visualTransitions`。
- 每页 `visual-extraction`、测量标注图和 `typography-calibration` 已落盘；每个最终可编辑对象有 `sourceExtractionId`、`coordinateCalibrationId`、原 PPTX 对象或明确来源说明。
- 每页 `coordinateTransform`、6-12 个自动宏观锚点、临时校准层和 `coordinateCalibration.status = PASS` 已落盘；最终 deck 不包含临时整页参考图。
- 低置信文字、形状、图片和间距对象已进入风险列表并闭环；复杂低置信对象自动选择 `baked-asset` 或 Mode B fallback，不得把未解释对象静默写入最终 PPTX。
- 标题、正文、标签和页码等主要文字样式已在 `acceptanceRenderer` 中完成 2-4 个候选渲染比较，并记录 bbox、baseline、wrap 和 overflow。
- 同一语义行、口号或标题中的多色/多字号强调已优先实现为单文本框富文本 runs；如拆成多个文本框，必须有独立布局原因，并记录拆分后的视觉间距证据。
- 富文本 runs 的颜色、字号、字重和描边在最终渲染 PNG 中保持区分；不能因合并文本框而退化为统一样式。
- `assets/templates/level-2-delivery-checklist.md` 已逐项完成。

### Level 2 必须视觉门禁

视觉 QA 是双门禁：文字可读性和参考图还原度必须分别通过。

- 底图无标题、正文、标签、页码和装饰线残留。
- contact sheet 已检查，但不能代替逐页全尺寸 PNG。
- 每页最终 PNG 已做图像识别审计。
- 视觉检查整页优先；不得把多轮裁剪作为默认审计流程。
- 整页放大只用于检查文字是否清晰、完整、被遮挡或裁切，不用于从 AI 伪字中恢复准确文案。
- 渲染 PNG 中的文字没有裁切、越界、破坏性重叠或安全间距不足。
- 同一句多样式文字在最终 PNG 中保持连续阅读节奏，没有因文本框不重叠规则产生异常空隙。
- 形状与形状、图片与图片、图片与非文字形状之间的叠放不纳入通用碰撞门禁；只有影响文字可读性或违反明确分层规则时才判定失败。
- 参考图中有意的 shape/image 覆盖已记录为 `overlapPolicy`、`allowedOverlays` 或 `allowedVisualOverlaps`；不影响文字可读性时不得计入 `visualOverlapCount`。
- `visionAuditStatus = PASS` 且 `visualOverlapCount = 0`。
- 按 [visual-fidelity-qa.md](visual-fidelity-qa.md) 逐页检查版式、构图、层级、色彩、字体观感、间距节奏和关键素材。
- `visualFidelityStatus = PASS` 且 `majorFidelityDeviationCount = 0`。
- 分区 `regionMetrics` 中关键对象的 bbox、baseline 和间距偏差必须落入门槛；未达标对象进入自动返修。
- `autoIterationCount <= 3`、`autoFidelityBlocked = false`、未解决 required editability conflicts = 0。
- 按 [visual-transition-strategy.md](visual-transition-strategy.md) 检查复杂过渡，`visibleAssetSeamCount = 0`；明显矩形接缝、色带、纹理中断或错误渐变方向按 `major` 处理。
- 不要求像素级完全一致；所有 `minor` 偏差必须逐页记录，未经解释的明显偏差不能通过。
- 普通形状或图片叠放即使不影响文字，只要其位置、层级、裁切或构图明显偏离参考图，仍属于还原度失败。
- 修复页使用新渲染图复审，不得复用旧预览。
- 连续两轮结论矛盾、同一区域反复 FAIL/PASS 或模型不能稳定判断时，标记 `needsHumanReview = true`，保留证据并请求人工裁决。

几何审计是预检，图像识别审计拥有否决权。`textFrameIntersections = 0` 不能证明文字无视觉重叠，也不能证明页面达到参考图目标。

### Level 2 可选增强

- 对形状数量偏多的页面补充角色分布图。
- 当参考图与渲染图尺寸、裁切和对齐完全一致时，可生成绝对差异热力图筛选候选区域；热力图不得单独决定 PASS/FAIL。

视觉重叠审计按 [visual-overlap-qa.md](visual-overlap-qa.md) 执行。

## Level 3 高还原 QA

用于 Mode C。

- Level 2 全部通过。
- 参考图 vs 渲染图并排图已检查。
- `visualFidelityStatus = PASS` 且 `majorFidelityDeviationCount = 0`。
- `unexpectedTextOverlapCount = 0`。
- `wholeReferenceImageEmbedded` 的状态、自动风险证据和人工对照结论证明未嵌入整页参考图。
- `combinedBackgroundPersonPictureCount = 0`，或 asset-audit 记录不可拆分例外。
- `contentPicturesAreIndependentObjects = true`。
- `coordinateCalibration.status = PASS`，临时校准层已验证，最终 deck 未包含整页参考图。
- `visualExtractionComplete = true`，每个分层对象有视觉抽取、资产审计、`coordinateCalibrationId` 或原 PPTX 来源。
- `typographyCalibrationComplete = true`，主要文字样式有同一 `acceptanceRenderer` 下的渲染校准证据。
- `autoIterationCount <= 3`，任何 `autoFallbacks` 和 `autoFidelityBlocked` 都已记录；存在阻断项时不得声明 Level 3 通过。
- `forbiddenOverlayShapesDetected = 0`。
- 背景、人物、内容图分层符合 asset-audit。
- 完成 [level-3-delivery-checklist.md](../assets/templates/level-3-delivery-checklist.md)。

Level 3 每项门槛都必须记录 `automatedEvidence`、`manualEvidence` 和 `status`。自动化无法证明的项目必须由人工证据闭环。

## Level 4 增量修改 QA

用于 Mode E。

- 备份文件存在。
- 源文件哈希已记录。
- 原文件未覆盖。
- 新文件另存。
- 用户文字、形状和位置未丢失。
- 只替换目标对象。

## 最终报告格式

报告输出路径、页数、`autonomyProfile`、`acceptanceRenderer`、`fontCandidateSet`、`coordinateCalibration`、临时校准层路径、字体槽位、未解析字体、媒体、对象角色、未知名称、图片覆盖风险、几何覆盖风险、渲染预览、任务输入、视觉抽取、字号校准、布局规格、视觉证据、`autoIterationCount`、`autoFallbacks`、`autoFidelityBlocked`、QA 等级、修复项、剩余风险和降级事件。

## 导出失败处理

不要默认请求提权。普通权限下导出或预览失败时：

1. 预创建输出目录。
2. 改到新版本目录。
3. 让 PPTX 保存早于预览。
4. 如果预览失败但 PPTX 存在，继续包内 QA。
5. 复用旧预览或旧 PPTX 时标记为回归测试，不能标记为完整新构建。
6. 遵循当前线程权限策略。
