# Semi Editable Workflow

Mode B 默认文字、表格、主要结构可编辑，复杂背景主视觉可合成。更轻的“仅文字可编辑”边界必须来自用户要求并记录。

1. 最小 task-input 记录来源、页序、B、executionProfile、编辑范围、渲染器和新输出路径；字体输出名可推断就直接选。
2. 按 [visual-extraction-pass.md](visual-extraction-pass.md) 抽取文案、bbox 和来源，再生成 layout-spec。
3. 复用原件和内容图；纯色背景、规则结构直接重画。必要时制作无字底图，同时搭文字、表格和形状。
4. 构建保存 PPTX，渲染初版。默认不为每页先造校准 deck 和 2–4 个字体候选。
5. 包内/几何审计，一次逐页对照完成文字可读性与参考图还原度双门禁。
6. 按 [adaptive-verification.md](adaptive-verification.md) 定向校准返修；strict 按 [autonomous-calibration.md](autonomous-calibration.md)。
7. 按 [qa-standards.md](qa-standards.md) 与 [Level 2 检查表](../assets/templates/level-2-delivery-checklist.md) 验证。预算用尽仍有 major 就明确未通过，不能暗改模式。

底图比例跟随画布，不残留已重建文字和结构线。必须可替换内容图独立保留，复杂边缘融合按 visual-transition-strategy.md。连续正文一个文本框，多色标题用 runs，形状按角色命名，不拼碎片图形。
