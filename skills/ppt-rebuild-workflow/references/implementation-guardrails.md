# Implementation Guardrails

当需要实际构建 Mode B/C、诊断失败页、写最终报告或复核是否违规时加载本文件。SKILL.md 只保留常驻骨架；本文件保留执行细则和反例。

## 构建细则

### 语义

- 先写清页面一句话表达、阅读顺序、图片与文字归属关系。
- 局部语义错误先依据来源修正；只有用户要求新的设计方向才进入 Mode D。
- 用户本次明确提供的标题/正文优先，不改定稿、不自行润色；图片旧文字与定稿不同不再重新确认。
- 用户未提供部分的 AI 字形错误先查当前 PPTX 和可信业务原文，再结合页面上下文与术语恢复；已提供部分跳过 OCR/语义恢复。
- 高置信语义恢复必须记录候选文字和证据；存在多个合理候选时设置 `needsHumanReview`，未经确认不得写成确定文案。

### 视觉抽取和坐标

- Mode B/C 先按 `visual-extraction-pass.md` 建立逐页 `visual-extraction`，再转成 `layout-spec` 和 `style-spec`。
- 默认先抽取并构建初版；渲染后按风险校准。strict 需要计算锚点，不足时记录 INCONCLUSIVE；临时校准层只在诊断需要时创建。
- 每个可编辑文字、形状和内容图对象必须能追溯到参考图 bbox、原 PPTX 对象、用户文案或明确的风格复用依据之一。
- 复杂或低置信形状仅在已约定的编辑边界内进入 `baked-asset` 或 `mode-b-fallback`；只有用户强制要求其独立可编辑且无稳定原生实现时才设置 `needsHumanReview`。

### 文字

- 字号分组只用于样式校准，不能作为合并文本框的依据。
- 连续一段正文默认一个文本框；不要把三行正文拆成三个文本框。
- 同一语义行、同一句口号或同一阅读流中的多色、多字号、粗细强调，优先用一个 PPT 文本框的富文本 runs 表达；不要因为颜色或字号变化拆成多个相邻文本框。
- 富文本合并必须保留每个 run 的颜色、字号、字重和必要描边；不能只合并字符串后套统一文本样式。使用 artifact-tool 时，先设置文本框基准样式，再写入带 `textStyle.color/fill` 的 runs，或在写入后对 range 设置样式，并用最终 PNG 复查。
- 只有当片段属于独立对齐、独立换行、独立旋转、独立动画、独立遮罩或非连续阅读对象时，才拆成多个文本框；拆分必须记录在 `text-box-policy`。
- 字号以 PowerPoint pt 为最终交付意图，优先使用偶数整数 pt；但必须记录构建运行时的实际单位和渲染后 bbox。
- 首版直接使用目标或本地可用字体；风险样式或 strict 才使用 2–4 个渲染候选，尽量批量放入一个探针 deck；不得用自动缩小文字逃避溢出。

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

### 多页和命名

- 逐页 layout-spec 保留对象来源；style-spec 和组件可共享，页面差异单独记录，不能为填表复制整套样式。
- 优先维护一份统一布局数据；公共模板、样式与数据集复用，完整逐页布局由程序展开。没有额外样式说明需要时，不再手写重复的 style-spec。
- 用户要求统一模板时，公共页头、字体层级和边距统一，AI 出图的小幅漂移归一化；实际观测仍保留，内容导致的不同栏宽、图数和文本框调整允许逐页覆盖。
- 不要用整批统一缩放替代逐页调参。
- Mode B 和 Mode C 使用完整角色前缀：`background-*`、`person-*`、`content-image-*`、`title-*`、`subtitle-*`、`kicker-*`、`body-text-*`、`tag-*`、`page-number-*`、`body-panel-*`、`footer-line-*`、`border-*`、`shade-*`、`decor-line-*`。
- 文本 `p:sp`、普通 shape 和 `p:pic` 分类型审计；`unknownRoleNames` 中的对象必须逐项解释。

## 最终报告最小内容

- 输出 PPTX 路径、页数、字体、媒体、文本对象、形状、自动降级和未完成风险。
- `target_font` 与包内字体是否一致；文本是否可编辑。
- 逐页 visual-extraction、layout-spec 与对照路径；fast/balanced 的 renderVerification，或 strict/触发项的计算校准证据。
- `text-box-policy`、`shape-role-summary`、`unknownRoleNames`、图片媒体数量和空媒体检查。
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
- 初版已有字高、换行或裁切问题，却不做定向字体校准。
- 把构建 API 的字号单位、PPT pt 和渲染像素混为一谈，只比较请求参数而不比较最终字形 bbox。
- 对无法稳定辨别的复杂轮廓强行画成原生形状，而不是自动选择 `baked-asset` 或 Mode B 回退。
- 未结合用户模板要求与内容差异，盲目把所有页面套成同一套位置和字号参数；或在已要求统一模板时反复复现 AI 出图的随机漂移。
- 未判断过渡复杂度，直接用窄透明矩形补救错误裁切、底色不匹配或复杂图片边缘。
- 只看 contact sheet，不看关键页全尺寸渲染。
- 把 `textFrameIntersections = 0` 误当成视觉无重叠；该指标不覆盖文字与装饰线、边框、图片边缘等碰撞。
- 只检查文字是否可读，却不检查重构后的版式、构图、层级、色彩和整体观感是否达到参考图目标。
- 只检查对象参数，不检查最终渲染后的字形像素。
- 把 AI 生成的伪字当作低分辨率文字，反复裁剪、放大或 OCR，而不结合原文案和业务语境恢复。
- 子 agent 各自决定风格，造成多页漂移。
- 普通权限下预览写入失败时直接请求提权，而不是先降级记录并继续包内 QA。
