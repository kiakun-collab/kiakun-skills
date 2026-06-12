---
name: ppt-rebuild-workflow
description: Use when rebuilding slide screenshots, image-only PPTX files, AI-generated reference slides, or user-edited PowerPoint drafts into editable PPTX deliverables.
---

# PPT Rebuild Workflow

## 核心原则

先判定任务模式，再制作 PPT。不要把“生成一个 PPTX 文件”当成目标；目标是按用户要求在速度、可编辑性、还原度之间选择正确模式，并用渲染和包内 QA 证明结果。

- 参考图决定视觉目标、坐标、间距、层级、裁切和文字观感，但参考图不天然正确。
- Mode B/C 的目标是忠实达到参考图，不得要求超越参考图，也不得擅自重新设计；只有用户明确要求改版或提升时才另行建立新视觉目标。
- 原 PPTX 或用户给定文档负责准确文案、业务逻辑、内容顺序和可复用资产。
- AI 参考图中的错字、乱码和伪字按 [text-recovery.md](references/text-recovery.md) 做有来源的语义重建；不得通过裁剪、放大或视觉猜字替代文案核对。
- 文字必须优先使用 PPT 文本框；结构元素优先使用 PPT 原生形状。
- 除非用户明确选择快览模式，不要把整页参考图直接嵌入最终可编辑稿。
- 不覆盖用户原文件；输出新文件名和新版本目录。
- 字体作为 `target_font` 输入确认；用户未指定时先问一次。
- 默认坐标系为 1280 x 720。非 16:9 任务必须先确认是扩展坐标规则还是接受降级，不能擅自声明仅支持 16:9。

## 运行时职责

当 `presentations:Presentations` 同时激活时，PPTX 构建、导入、导出和渲染遵循其 artifact-tool 契约；本 Skill 只补充模式、语义、可编辑边界和 QA。图片重构不适用其通用的“超越参考图”评分，完整边界见 [runtime-integration.md](references/runtime-integration.md)。

## 输入确认

开始前确认这些参数，缺少关键项时先补齐：

- `task_mode`：快版整页图 / 半可编辑重构 / 完全分层重构 / 先重做参考图 / 增量修改。
- `target_font`：目标字体。
- `source_pptx`：原 PPTX 或用户已修改 PPTX，若有。
- `source_copy`：原始文案、创意说明、策划稿、术语表或其他可信业务资料。
- `reference_images`：参考图目录或逐页图片路径。
- `slide_order`：页序；文件名和画面编号冲突时以用户说明或画面编号为准。
- `editable_boundary`：哪些对象允许烘焙进图，哪些对象必须可编辑。
- `asset_strategy`：复用原图、生成无字底图、人物透明 PNG、内容图独立对象等。
- `qa_level`：Level 1 / 2 / 3 / 4。
- `output_name`：新输出文件名。
- `overwrite_policy`：默认禁止覆盖。

使用 [task-input-template.json](assets/templates/task-input-template.json) 记录输入。Mode B 和 Mode C 在构建前必须把关键字段落盘；不能只依赖会话记忆。

## 任务模式

按 [mode-selection.md](references/mode-selection.md) 选择模式。

- **Mode A 快版整页图 PPT**：每页一张完整图，只用于预览和方向确认。
- **Mode B 半可编辑重构**：一张无字底图 + 可编辑文字和结构层。分隔页、速度优先但仍需编辑时优先选择。细节见 [semi-editable-workflow.md](references/semi-editable-workflow.md)。
- **Mode C 高还原完全分层重构**：纯背景、人物、内容图、文字、形状全部分层。细节见 [full-layered-workflow.md](references/full-layered-workflow.md)。
- **Mode D 先重做参考图**：参考图语义或版式错误时先生成候选参考图。细节见 [mode-d-workflow.md](references/mode-d-workflow.md)。
- **Mode E 用户修改稿增量修正**：只替换目标对象，保留用户当前文件内容。细节见 [incremental-edit-workflow.md](references/incremental-edit-workflow.md)。

## 构建规则

1. **语义先行**
   - 先写清页面一句话表达、阅读顺序、图片与文字归属关系。
   - 如果参考图错误理解内容，停止 PPT 构建，转入 Mode D。

2. **文字**
   - 不改原文案，不自行润色，不扩散参考图错字。
   - AI 图像中的字形错误不是普通 OCR 问题。先查原 PPTX、用户文案和可信业务资料，再结合页面上下文、全稿术语和内容逻辑恢复。
   - 高置信语义恢复必须记录候选文字和证据；存在多个合理候选时设置 `needsHumanReview`，未经确认不得写成确定文案。
   - 连续一段正文默认一个文本框；不要把三行正文拆成三个文本框。大号标题、多色强调、特殊排版可例外。
   - 字号以 PowerPoint pt 为准，优先使用偶数整数 pt，除非用户或模板另有要求。

3. **形状**
   - 卡片、标签、边框、分隔线、页码线、结构阅读区用 PPT 原生形状。
   - 一个视觉角色尽量对应一个形状；不要用大量小形状拼出本可用原生属性表达的元素。
   - 已在 `layout-spec` 记录的简单规则渐变可用原生形状；纹理、光晕、雾气、图片单侧渐隐等复杂过渡按 [visual-transition-strategy.md](references/visual-transition-strategy.md) 处理。
   - 不用未规划的窄透明矩形补救错误裁切、底色不匹配或复杂图片边缘。
   - Mode B 和 Mode C 必须使用完整角色前缀：`background-*`、`person-*`、`content-image-*`、`title-*`、`subtitle-*`、`kicker-*`、`body-text-*`、`tag-*`、`page-number-*`、`body-panel-*`、`footer-line-*`、`border-*`、`shade-*`、`decor-line-*`。
   - 文本 `p:sp`、普通 shape 和 `p:pic` 分类型审计；`unknownRoleNames` 中的对象必须逐项解释。

4. **图片**
   - Mode B 允许“背景环境 + 主视觉”合成一张无字底图。
   - Mode C 默认纯背景、人物、内容图分离。
   - 内容图、截图、证据图需要可替换时必须独立图片对象。
   - 复杂氛围过渡可以烘焙进透明图片或无字底图，但文字、标签和结构仍按模式要求保持可编辑。
   - 整页参考图只用于 QA；除 Mode A 外禁止嵌入最终稿。

5. **多页**
   - 可以共用组件函数，但必须实际产出逐页 `layout-spec` 文件；`layout-spec` 和 `style-spec` 参数必须逐页独立。
   - 不要用整批统一缩放替代逐页调参。

## 推荐流程

1. 冻结任务边界和输出路径。
2. 判定任务模式和 QA 等级。
3. 做页面语义验收和异常文字恢复。
4. 建立资产策略，并按 [visual-transition-strategy.md](references/visual-transition-strategy.md) 记录关键渐隐、光晕和图片边缘的实现方式。
5. 建立逐页 `layout-spec` 和 `style-spec`。
6. 并行推进图像处理、PPT 构建脚手架、文字审计和底图 QA。
7. 构建 PPTX。
8. 重新导入或渲染导出的 PPTX。
9. 先运行包内和几何审计，再对最终渲染 PNG 做逐页图像识别审计。
10. 执行视觉 QA 双门禁：先检查文字可读性，再检查版式、构图、层级、色彩和整体观感是否达到参考图目标。
11. 修复所有阻断级文字碰撞和重大还原偏差，重新渲染并复审；不得用旧渲染图代替复审。
12. 按 QA 等级检查，至少修复一轮明显偏差。
13. 交付新版本，并报告文件路径、页数、字体、媒体、文本对象、形状和未完成风险。

Mode B Level 2 交付前逐项完成 [level-2-delivery-checklist.md](assets/templates/level-2-delivery-checklist.md)。

## 失败降级

本地导出、渲染或预览写入失败时，不要默认请求提权。先用普通权限处理：

- 预创建输出、预览和 QA 目录。
- 改到新的版本目录或临时目录。
- 先保存 PPTX，再尝试渲染预览。
- 如果预览失败但 PPTX 已生成，继续做包内 QA，并把预览失败写进最终报告。
- 如果构建脚本顺序导致预览失败阻塞 PPTX 输出，修改脚本让 PPTX 保存早于预览，或跳过预览并记录失败。

只有用户明确允许提权或当前环境支持审批时，才考虑请求更高权限。

## 子 Agent 协作

仅在当前平台允许且用户明确授权时使用子 agent。子 agent 只做审计、转写、检查和建议；主线程统一合并参数和修改构建脚本。可用任务模板见 [subagent-prompts.md](references/subagent-prompts.md)。

适合分发：

- 逐页文案转写和错字检查。
- 基于来源和上下文的异常文字语义恢复。
- 参考图 vs 渲染图视觉审计。
- 最终渲染文字可读性审计。
- 无字底图残留文字、标签、页码检查。
- 包内 QA 复核。
- 单页 `layout-spec` 草稿。

不适合分发：

- 多页统一风格决策。
- 最终参数合并。
- 多个线程同时修改同一个构建脚本。

## QA 必做项

按 [qa-standards.md](references/qa-standards.md) 执行。

最终报告至少包含：

- 输出 PPTX 路径和页数。
- `target_font` 与包内字体是否一致。
- 文本是否可编辑。
- 形状和文本框是否有明显冗余。
- `text-box-policy`：说明连续正文是否保持为单个文本框，以及哪些拆分属于标题、多色强调或特殊结构。
- `shape-role-summary`：按完整角色词典分别说明文本 shape、普通 shape 和图片数量，并列出 `unknownRoleNames`。
- 渲染预览路径或 contact sheet 路径。
- 图片媒体数量和空媒体检查。
- 逐页 `layout-spec` 文件路径。
- 参考图与渲染图对照图路径。
- `textFrameIntersections`，Mode B Level 2 必须为 `0`。
- `thinShapeTextFrameIntersections`：细长装饰形状与文本框相交候选；未解释的候选必须修复。
- `unresolvedTextFrameCount`、`unresolvedGroupTransformCount` 和 `geometryCoverageRisks`：非零时不能沉默通过。
- `fullSlideImageRiskPages` 与 `wholeReferenceImageEmbedded` 证据状态。
- `visionAuditStatus` 和 `visualOverlapCount`；Mode B Level 2 必须为 `PASS` 和 `0`。
- `visualFidelityStatus` 和 `majorFidelityDeviationCount`；Mode B/C 必须为 `PASS` 和 `0`。
- `visibleAssetSeamCount`、`transitionFlaggedPages` 和 `visualTransitionByPage`；明显矩形接缝或错误渐变方向必须按重大还原偏差返修。
- `visualFidelityByPage`：逐页记录版式、构图、层级、色彩、字体观感、间距和关键素材偏差。
- 逐页视觉审计报告路径、标记页和复审渲染图路径。
- `textRecovery`：来源文件、已恢复项、未决项和人工复核状态。
- 每页长正文文本框候选数量；普通分隔页默认每页恰好 `1` 个。
- 已知风险和下一轮建议。

缺少任务输入文件、逐页 `layout-spec`、视觉审计报告或必要审计产物时，不得把 Level 2 标记为完整通过。

## 常见错误

- 把 Mode B 误做成 Mode A，导致文字和结构不可编辑。
- 等图像生成时主线程空等，没有并行构建 PPT 结构和文字层。
- 背景正确后忽略文字大小、颜色、行距、标签宽高和垂直节奏。
- 多页套同一套位置和字号参数。
- 未判断过渡复杂度，直接用窄透明矩形补救错误裁切、底色不匹配或复杂图片边缘。
- 只看 contact sheet，不看关键页全尺寸渲染。
- 把 `textFrameIntersections = 0` 误当成视觉无重叠；该指标不覆盖文字与装饰线、边框、图片边缘等碰撞。
- 只检查文字是否可读，却不检查重构后的版式、构图、层级、色彩和整体观感是否达到参考图目标。
- 只检查对象参数，不检查最终渲染后的字形像素。
- 把 AI 生成的伪字当作低分辨率文字，反复裁剪、放大或 OCR，而不结合原文案和业务语境恢复。
- 子 agent 各自决定风格，造成多页漂移。
- 普通权限下预览写入失败时直接请求提权，而不是先降级记录并继续包内 QA。
- 忽略当前权限策略，或在已有目录可复用时仍无依据请求提权。

## 模板

可复制 `assets/templates/` 中的模板建立任务输入、任务派发、资产审计、布局规格、样式规格和 QA 报告。

- Mode B 布局参考：[layout-spec-mode-b-example.json](assets/templates/layout-spec-mode-b-example.json)。
- Mode C 布局参考：[layout-spec-mode-c-example.json](assets/templates/layout-spec-mode-c-example.json)。
- 示例中的对象按实际页面删减，不能把示例内容原样带入成品。

## 脚本

- `scripts/audit_pptx_structure.py`：只读 PPTX 包内 XML，分槽位审计 slide/layout/master/theme 字体，统计对象角色和图片覆盖率。
- `scripts/audit_pptx_text_frames.py`：只读检查 connector、直接或继承文本框、旋转/组合对象覆盖风险、几何相交和长正文候选。
- `scripts/make_reference_render_comparison.py`：按文件名页码或显式 manifest 配对，生成对照图和 pairing JSON。

命令、参数和输出字段见 [script-output-contracts.md](references/script-output-contracts.md)。修改脚本输出时必须同步更新该契约和 QA 模板。

文字可读性审计见 [visual-overlap-qa.md](references/visual-overlap-qa.md)；参考图还原度审计见 [visual-fidelity-qa.md](references/visual-fidelity-qa.md)；复杂渐隐与边缘融合见 [visual-transition-strategy.md](references/visual-transition-strategy.md)。
