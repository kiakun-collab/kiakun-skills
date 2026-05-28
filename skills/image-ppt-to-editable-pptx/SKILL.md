---
name: image-ppt-to-editable-pptx
description: Use when converting image-only PPT slides, slide screenshots, reference page images, or raster presentation comps into editable PowerPoint PPTX files, especially when users require editable text, native shapes, parameterized fonts, image placeholders, background fidelity, and post-export render/overflow/package QA.
---

# Image PPT To Editable PPTX

## 核心原则

把图片型 PPT 复刻为可编辑 `.pptx`。普通文字必须是文本框，结构元素优先使用 PPT 原生形状，截图/示例图区域只做单一占位形状，背景使用 PPT 页面背景格式。不要把字体写死；把字体作为任务参数 `target_font`。

## 输入确认

开始制作前确认这些参数：

- `target_font`：用户指定字体。未指定时先问一次，不要默认字体。
- `slide_order`：输出页顺序；若图片文件名顺序与画面编号冲突，以画面编号或用户说明为准。
- `output_name`：新文件名。用户提到旧文件已修改或不要覆盖时，必须创建新输出文件。
- `placeholder_policy`：默认截图、示例图、UI 截图、照片墙、视频画面都只做单一矩形占位，不还原内部细节。

## 构建规则

1. **文字**
   - 所有普通文字都创建为可编辑文本框。
   - 不改原文案，不改标点，不自行润色。
   - 所有文本框使用 `target_font`。
   - 字号以 PowerPoint 磅值为准，必须是偶数整数。若 authoring API 使用 px，先换算到偶数 pt，再回填 px。

2. **背景**
   - 使用 slide background / background fill API 设置页面背景。
   - 不创建整页矩形作为背景层。
   - 若当前工具无法设置背景，只能使用一个兜底整页形状，并在最终报告中说明。

3. **占位图**
   - 每个截图/示例图区域只能是一个 PPT 原生矩形形状。
   - 不在占位图内部拼小色块、线条、假缩略图、假 UI、模拟图片细节。
   - 占位形状命名应包含 `placeholder`，便于 QA 统计和用户选择删除。

4. **形状系统**
   - 卡片、边框、虚线、流程框、分隔线、箭头使用 PPT 原生形状属性。
   - 不用大量小形状拼出一个本可用原生属性表达的元素。
   - 相同角色的框保持一致尺寸、线宽、填充、对齐和内边距。

5. **图片资源**
   - 默认不嵌入原始参考图。
   - 只有用户明确要求保留某张图时才嵌入图片资源。
   - 若目标是“可编辑复刻”，截图区仍优先使用单一占位形状。

## 推荐流程

1. 读取参考图，拆解每页：标题、正文、编号、矩阵、流程、占位图片区、分隔线、页眉页脚。
2. 建立设计系统：页面尺寸、`target_font`、颜色、线宽、背景、占位图样式。
3. 新建 PPTX，不覆盖已有用户文件。
4. 用可编辑文本框和原生形状重建页面。
5. 导出 PPTX。
6. 重新导入导出的 PPTX 并渲染每页。
7. 做布局与包内检查，修复后再交付。

## QA 必做项

最终报告必须包含：

- 文件路径和页数。
- 字体：包内所有文字字体是否等于 `target_font`。
- 字号：是否全部为偶数整数 PowerPoint 磅值。
- 文本：重新导入/渲染后是否有溢出、裁切、重叠。
- 占位图：数量，以及是否每个占位区都是单一形状。
- 背景：是否使用 PPT 页面背景格式；是否存在整页背景形状。
- 形状数量：总形状数。
- 图片资源：`ppt/media` 文件数，是否嵌入图片。

## 包内检查建议

导出后解压 `.pptx` 检查：

- `ppt/slides/slide*.xml` 中的字体 `typeface`。
- `<a:rPr sz="...">` 字号，换算为 pt 后必须全为偶数整数。
- `<p:pic>` 和 `ppt/media`，确认是否嵌入图片。
- 占位形状名称中 `placeholder` 的数量。
- `<p:bg>` 背景标签数量。
- 是否存在覆盖整页尺寸的背景矩形。

## 常见错误

- 把占位图做成多个小形状，导致用户不能一键删除。
- 用多层全页矩形模拟背景，增加图层负担。
- 只在生成前检查，忽略导出后重新导入造成的换行、裁切和字号变化。
- 用 px 判断“偶数字号”，但 PowerPoint 实际显示为半号或奇数磅。
- 硬编码某个字体，导致不同 PPT 需求无法复用。
