# Implementation Guardrails

当需要实际构建 Mode B/C、诊断失败页、写最终报告或复核是否违规时加载本文件。SKILL.md 只保留常驻骨架；本文件保留执行细则和反例。

## 构建细则

### 语义

- 先写清页面一句话表达、阅读顺序、图片与文字归属关系。
- 如果参考图错误理解内容，停止 PPT 构建，转入 Mode D。
- 不改原文案，不自行润色，不扩散参考图错字。
- AI 图像中的字形错误不是普通 OCR 问题。先查原 PPTX、用户文案和可信业务资料，再结合页面上下文、全稿术语和内容逻辑恢复。
- 高置信语义恢复必须记录候选文字和证据；存在多个合理候选时设置 `needsHumanReview`，未经确认不得写成确定文案。

### 视觉抽取和坐标

- Mode B/C 先按 `visual-extraction-pass.md` 建立逐页 `visual-extraction`，再转成 `layout-spec` 和 `style-spec`。
- `auto-calibrated` 必须先完成临时校准层、坐标变换和 3-12 个稳定自动宏观锚点；少于 3 个时必须标记 `INSUFFICIENT`，参考整图只能存在于临时产物，不得进入最终 deck。
- 每个可编辑文字、形状和内容图对象必须能追溯到参考图 bbox、原 PPTX 对象、用户文案或明确的风格复用依据之一。
- 复杂或低置信形状默认进入 `baked-asset` 或 `mode-b-fallback`；只有用户强制要求其独立可编辑且无稳定原生实现时才设置 `needsHumanReview`。

### 文字

- 连续一段正文默认一个文本框；不要把三行正文拆成三个文本框。
- 同一语义行、同一句口号或同一阅读流中的多色、多字号、粗细强调，优先用一个 PPT 文本框的富文本 runs 表达；不要因为颜色或字号变化拆成多个相邻文本框。
- 富文本合并必须保留每个 run 的颜色、字号、字重和必要描边；不能只合并字符串后套统一文本样式。使用 artifact-tool 时，先设置文本框基准样式，再写入带 `textStyle.color/fill` 的 runs，或在写入后对 range 设置样式，并用最终 PNG 复查。
- 只有当片段属于独立对齐、独立换行、独立旋转、独立动画、独立遮罩或非连续阅读对象时，才拆成多个文本框；拆分必须记录在 `text-box-policy`。
- 字号以 PowerPoint pt 为最终交付意图，**应为偶数整数 pt**（`audit_pptx_structure.py` 的 `nonEvenFontSizesPt` 会列出非偶数整数 pt 的字号，交付前应清零或逐个说明）；不要用 px 判断"偶数"，px 偶数在 PowerPoint 里可能显示为半号或奇数磅。必须同时记录构建运行时的实际单位和渲染后 bbox。
- 标题、正文、标签和页码必须用 2-4 个渲染候选校准字号、行距、文本框宽高和内边距；不得用自动缩小文字逃避溢出。

### 形状和图片

- 卡片、标签、边框、分隔线、页码线、结构阅读区用 PPT 原生形状。
- 一个视觉角色尽量对应一个形状；不要用大量小形状拼出本可用原生属性表达的元素。
- 形状必须先进入 `visual-extraction.shapes[]`：记录类型、bbox、圆角、填充、描边、透明度、阴影、层级、置信度和实现策略。
- 已在 `layout-spec` 记录的简单规则渐变可用原生形状；纹理、光晕、雾气、图片单侧渐隐等复杂过渡按 `visual-transition-strategy.md` 处理。
- 不用未规划的窄透明矩形补救错误裁切、底色不匹配或复杂图片边缘。
- Mode B 允许“背景环境 + 主视觉”合成一张无字底图；Mode C 默认纯背景、人物、内容图分离。
- 内容图、截图、证据图需要可替换时必须独立图片对象。
- 复杂氛围过渡可以烘焙进透明图片或无字底图，但文字、标签和结构仍按模式要求保持可编辑。
- 整页参考图只用于 QA；除 Mode A 外禁止嵌入最终稿。
- 标签、遮罩、角标或装饰形状按参考图覆盖图片时，记录 `overlapPolicy` 或 `allowedOverlays`；只要不影响文字可读性，不计入视觉重叠失败。

### 占位图规范

- 截图、示例图、UI 截图、照片墙、视频画面等**无需内部可编辑还原**的区域，默认只做**单一原生占位对象**（`content-image-*` 独立图片对象，或按可表达性评分走 `baked-asset`）。
- **禁止**在占位区内部拼小色块、线条、假缩略图、假 UI、模拟图片细节——那会让用户无法一键删除、也拖垮图层数。
- 占位对象必须带角色前缀命名（如 `content-image-01`），便于 `audit_pptx_structure.py` 的 `pictureRoleCounts` 统计与用户按角色选择删除。
- `独立图片对象` 用于用户明确要保留/可替换的图；仅需占位、不保留原图时优先单一形状 + `baked-asset`，不默认嵌入原始参考图（整页参考图除 Mode A 外禁止入最终稿）。

### 背景规范

- 页面纯色或规则渐变底色优先用 **PPT 页面背景格式（slide background fill / `<p:bg>`）**，不要创建覆盖整页的矩形当"背景层"徒增图层。
- 仅当构建后端无法设置页面背景时，才允许一个兜底整页形状，并在最终报告注明。
- 区分两个概念：Mode B/C 合成的"背景环境无字底图"是**内容素材**（`background-*` 角色的图片对象），与"纯色页面底色"不同——后者应走 bg fill，不做整页矩形。
- QA 必查：是否存在覆盖整页尺寸的实心背景矩形（应改为页面背景格式）。

### 角色一致性

- 相同视觉角色的框（卡片、标签、面板、分隔线）保持一致的尺寸档、线宽、填充、对齐和内边距；同角色对象不应在不同页出现不必要的参数漂移。

### 多页和命名

- 可以共用组件函数，但必须实际产出逐页 `layout-spec` 文件；`layout-spec` 和 `style-spec` 参数必须逐页独立。
- 不要用整批统一缩放替代逐页调参。
- Mode B 和 Mode C 使用完整角色前缀：`background-*`、`person-*`、`content-image-*`、`title-*`、`subtitle-*`、`kicker-*`、`body-text-*`、`tag-*`、`page-number-*`、`body-panel-*`、`footer-line-*`、`border-*`、`shade-*`、`decor-line-*`。
- 文本 `p:sp`、普通 shape 和 `p:pic` 分类型审计；`unknownRoleNames` 中的对象必须逐项解释。

## 最终报告最小内容

- 输出 PPTX 路径、页数、字体、媒体、文本对象、形状、自动降级和未完成风险。
- `target_font` 与包内字体是否一致；文本是否可编辑。
- 逐页 `visual-extraction`、测量标注图、typography calibration、`layout-spec`、参考图与渲染图对照路径。
- `text-box-policy`、`shape-role-summary`、`unknownRoleNames`、图片媒体数量和空媒体检查。
- 占位图数量，及每个占位区是否为单一形状（无内部假细节）；背景是否使用 PPT 页面背景格式、是否存在整页背景矩形；`nonEvenFontSizesPt`（非偶数整数 pt 字号）是否清零。
- `textFrameIntersections`、`thinShapeTextFrameIntersections`、`unresolvedTextFrameCount`、`unresolvedGroupTransformCount` 和 `geometryCoverageRisks`。
- `fullSlideImageRiskPages`、`wholeReferenceImageEmbedded`、`visionAuditStatus`、`visualOverlapCount`。
- `visualFidelityStatus`、`majorFidelityDeviationCount`、`visibleAssetSeamCount`、`transitionFlaggedPages`、`visualTransitionByPage`。
- `visualFidelityByPage`、`visualExtractionByPage`、逐页视觉审计报告、标记页和复审渲染图路径。
- `textRecovery`：来源文件、已恢复项、未决项和人工复核状态。
- `autonomyProfile`、`coordinateCalibration`、临时校准层路径、渲染后端、`fontCandidateSet`、文字 bbox 指标、自动返修次数和自动降级记录。

缺少任务输入文件、逐页 `layout-spec`、视觉审计报告或必要审计产物时，不得把 Level 2 标记为完整通过。

## 常见错误

- 把 Mode B 误做成 Mode A，导致文字和结构不可编辑。
- 等图像生成时主线程空等，没有并行构建 PPT 结构和文字层。
- 背景正确后忽略文字大小、颜色、行距、标签宽高和垂直节奏。
- 把同一句多色标题、口号或强调句拆成多个文本框，再用 `textFrameIntersections = 0` 强行拉开，导致一句话中间出现不符合参考图的大空隙。
- 把多色文本合并成一个文本框后没有保留 run 级样式，导致后半句颜色、字号或粗细被统一成同一种样式。
- 跳过视觉抽取，直接按肉眼印象填写坐标、形状和字号。
- 把临时参考页误当成最终稿，或以为把图片放进 PPT 就能自动解决视觉理解和坐标误差。
- 要求用户逐页确认大量锚点，而不是先用自动坐标锁、校准叠加和渲染回调闭环。
- 先写 `layout-spec` 或构建 PPT，再倒填测量 JSON、标注图和 `sourceExtractionId` 伪装成已有证据。
- 只运行测量脚本就把候选框当作最终形状清单，没有逐页复核误报、漏报、圆角、层级和可编辑策略。
- 未建立 `visual-extraction.shapes[]`，直接把不确定轮廓猜成圆角矩形、自由形状或大量无名小形状。
- 只估一个字号，不做候选渲染校准，导致字高、行距和文本块边界漂移。
- 把构建 API 的字号单位、PPT pt 和渲染像素混为一谈，只比较请求参数而不比较最终字形 bbox。
- 对无法稳定辨别的复杂轮廓强行画成原生形状，而不是自动选择 `baked-asset` 或 Mode B 回退。
- 多页套同一套位置和字号参数。
- 未判断过渡复杂度，直接用窄透明矩形补救错误裁切、底色不匹配或复杂图片边缘。
- 只看 contact sheet，不看关键页全尺寸渲染。
- 把 `textFrameIntersections = 0` 误当成视觉无重叠；该指标不覆盖文字与装饰线、边框、图片边缘等碰撞。
- 只检查文字是否可读，却不检查重构后的版式、构图、层级、色彩和整体观感是否达到参考图目标。
- 只检查对象参数，不检查最终渲染后的字形像素。
- 把 AI 生成的伪字当作低分辨率文字，反复裁剪、放大或 OCR，而不结合原文案和业务语境恢复。
- 子 agent 各自决定风格，造成多页漂移。
- 普通权限下预览写入失败时直接请求提权，而不是先降级记录并继续包内 QA。
- 把占位图/截图区做成多个小形状或拼假内部细节，导致用户不能一键删除、图层暴涨。
- 用整页实心矩形当背景层，而不是用 PPT 页面背景格式。
- 用 px 判断"偶数字号"，实际 PowerPoint 显示为半号或奇数磅。
