# Semi Editable Workflow

用于一页一张无字底图、上层文字和结构可编辑的 PPT 重构。适合分隔页、速度优先、但仍需要修改文案和版式的任务。

样式参数使用 [style-spec-template.md](../assets/templates/style-spec-template.md)，最终报告使用 [qa-report-template.json](../assets/templates/qa-report-template.json)。

## 输入

- 参考图或无字底图目录。
- `target_font`。
- `autonomy_profile`：默认 `auto-calibrated`；用户要求人工逐对象确认时才使用 `human-assisted`。
- `acceptance_renderer`：用于字体探针和最终视觉门禁的渲染后端。
- 页序。
- 输出文件名。
- 允许烘焙的对象：背景环境 + 主视觉。
- 必须可编辑的对象：文字、标签、正文框、页码、装饰线、边框、结构阅读区。

## 流程

1. 确认 Mode B，不把完整参考图直接嵌入最终稿。
2. 对每页转写文字：栏目名、主标题、副标题、标签、正文、页码。
3. 按 [autonomous-calibration.md](autonomous-calibration.md) 锁定坐标：运行测量脚本，生成带自动锚点的标注图和临时校准层。该层只用于验证，不进入最终 PPTX。
4. 按 [visual-extraction-pass.md](visual-extraction-pass.md) 建立视觉抽取：自动修正候选文字、形状、图片和间距 bbox，并为低置信复杂对象选择 `baked-asset` 或 `mode-b-fallback`。
5. 为每页建立 `typography-calibration`：用同一渲染后端比较 2-4 个字号、行距、文本框宽高、内边距和字体候选，不只保留一个猜测值。
6. 参考 `assets/templates/layout-spec-mode-b-example.json` 建立并落盘逐页 `layout-spec` 文件：所有主要元素的 `x/y/w/h`、字号、颜色、行距、间距，并写入 `sourceExtractionId` 与 `coordinateCalibrationId`。
7. 建立逐页 `style-spec`：标题层级、标签样式、正文框样式、线条和边框样式，并记录参考 bbox 与渲染校准证据。
8. 识别渐隐、光晕、雾气和图片边缘融合区，按 [visual-transition-strategy.md](visual-transition-strategy.md) 填写 `visualTransitions`。
9. 如果需要生成无字底图，图像生成和 PPT 结构搭建并行推进。
10. 插入无字底图作为底层图片；复杂过渡在图片阶段完成，简单规则渐变才使用原生形状。
11. 使用 PPT 文本框和原生形状重建文字与结构。
12. 导出 PPTX 并由 `acceptance_renderer` 渲染 PNG。
13. 运行文本框、细长形状与包内结构审计。
14. 对每页最终 PNG 做图像识别视觉重叠审计和分区还原度审计。
15. 自动修复标记问题并重新导出、重新渲染、重新审计，最多三轮；仍失败时使用 Mode B 可编辑边界内的最小烘焙回退。
16. 做 Level 2 QA；发生自动回退或未达指标时不得标记为完整通过。

## Level 2 硬门槛

完整门槛只以 [qa-standards.md](qa-standards.md) 和 [level-2-delivery-checklist.md](../assets/templates/level-2-delivery-checklist.md) 为准。本工作流额外要求坐标校准与字体校准来自对应脚本的计算证据；手填 PASS 不生效。

## 导出和预览降级

遵循 [SKILL.md 的失败降级](../SKILL.md#失败降级)，不要在本工作流维护另一套规则。

## 底图要求

- 16:9。
- 无标题、正文、标签、页码、装饰线和 UI 框。
- 构图接近参考图。
- 文字区域有足够负空间。
- 主视觉位置和尺度接近参考图。
- 复杂氛围过渡包含在底图或透明资产中，素材裁切边界不落在可见过渡区。

## 文字对象规则

- 连续正文默认一个文本框，使用段落换行。
- 同一标签文字为一个文本框或形状内文本。
- 主标题、底部口号和强调句若属于同一阅读流，默认一个文本框，颜色、字号、粗细差异用富文本 runs 表达。
- 主标题只有在独立对齐、独立换行、独立旋转、独立动画、遮罩或非连续阅读对象时才拆多个文本框，并在 `text-box-policy` 解释。
- 不要把三行普通正文拆成三个文本框。
- QA 报告必须包含 `text-box-policy`：列出正文、标题、标签、页码分别如何合并、使用富文本 runs 或拆分。

## 形状角色规则

- 构建时必须命名形状角色：`tag-*`、`body-panel-*`、`footer-line-*`、`border-*`、`shade-*`、`decor-line-*`。
- 一个标签胶囊原则上一个形状；标签文字可以是形状内文本或相邻文本框。
- 一个正文框原则上一个形状。
- 页码线和装饰线不要拆成过多碎片，除非参考图确实分段。
- QA 报告必须说明形状数量是否与页面结构复杂度匹配。
- Level 2 交付中不应出现无法识别角色的大量形状；少量未命名形状必须按页说明用途。

## 返修重点

- 标题重量和基线。
- 标签高度、宽度、内边距和单行显示。
- 正文框位置、尺寸、圆角、透明度。
- 正文字号、行距、颜色和段落间距。
- 文字块参考 bbox、字形 bbox、内边距和渲染后文本块高度是否与校准记录一致。
- 页码和底部线条位置。
- 左侧阅读区和主视觉边缘是否出现硬边、矩形接缝、色带或多余蒙层。
- 渐变方向、过渡宽度和纹理连续性是否达到参考图目标。
- 文字与装饰线、标签边框、图片高对比边缘是否发生视觉相切、穿越或遮挡。

视觉审计不能只看对象参数。文字框与线条即使没有被旧脚本计为“文本框相交”，最终字形仍可能被穿过；应按 [visual-overlap-qa.md](visual-overlap-qa.md) 检查渲染结果。
