# 单页任务派发模板

你只处理第 XX 页，不处理其他页面。

输入：

- 原 PPTX：
- 对应页码：
- 唯一参考图：
- 原始文案或业务资料：
- 术语表：
- 当前任务模式：
- 自动化档案：默认 `auto-calibrated`
- 目标字体：
- 接受渲染后端：
- 输出目录：

可编辑边界：

- 允许烘焙进图：
- 必须可编辑：
- 禁止覆盖：

任务：

1. 页面语义拆解和异常文字恢复。
2. 测量参考图并锁定坐标：运行 `scripts/extract_reference_measurements.py`，保存测量 JSON、标注图、`coordinateTransform` 和 3-12 个稳定自动宏观锚点；不足 3 个时不得继续声明校准通过。
3. 生成并验证临时校准层：把参考图只放入临时校准页，校验自动锚点偏移，保存 `coordinateCalibration.status`。
4. 复核测量结果并建立视觉抽取：记录文字、形状、图片、间距的 `x/y/w/h`、置信度、误报/漏报修正和测量证据；复杂低置信对象默认 `baked-asset` 或 Mode B fallback。
5. 在接受渲染后端中比较 2-4 个字体、字号、行距、文本框宽高和内边距候选，记录 bbox、baseline、wrap 和 overflow。
6. 资产策略。
7. layout-spec，所有对象带 `sourceExtractionId`、`coordinateCalibrationId` 或来源说明；不得先建 layout 再补测量。
8. style-spec，记录参考 bbox 和校准证据。
9. PPT 构建或审计。
10. 渲染 QA。
11. 自动返修建议；首次构建记为第 0 轮，最多返修 3 次，仍失败时记录最小自动回退。

硬门槛：

- 字体一致。
- 文本无明显重叠。
- 连续正文不拆成多个冗余文本框。
- 结构形状合理。
- 测量 JSON、自动锚点、临时校准层和标注图存在，主要对象的 `x/y/w/h` 已逐项记录，`coordinateCalibration.status = PASS`。
- 低置信形状不能无说明进入最终 PPTX；复杂低置信对象默认 `baked-asset` 或 Mode B fallback。
- 主要文字样式有最终渲染校准证据，不只保留猜测字号。
- 不嵌入整页参考图，除非 Mode A。
