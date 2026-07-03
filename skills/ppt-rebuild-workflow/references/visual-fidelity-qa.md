# Visual Fidelity QA

输出使用 [visual-fidelity-audit-template.json](../assets/templates/visual-fidelity-audit-template.json)。

用于判断最终 PPT 重构是否达到参考图的视觉目标。视觉 QA 采用双门禁：

1. 文字可读性门禁：文字清晰、完整，没有破坏性遮挡、裁切或重叠。
2. 参考图还原度门禁：版式、构图、层级、色彩、字体观感、间距节奏和关键素材达到当前模式约定。

两项必须分别记录和通过。文字完全可读，不代表重构程度达标。

## 比较原则

- 使用页码已校验的参考图与最终渲染图做整页并排比较。
- 参考图是忠实重构目标。不得要求超越参考图，也不得因审计者个人审美奖励未经用户授权的重新设计。
- 不要求像素级完全一致。不同渲染引擎、字体抗锯齿和可编辑对象重建会产生合理差异。
- 参考图不是准确文案来源。AI 伪字按 `text-recovery.md` 恢复后，以正确文字替代错误字形不算视觉偏差。
- 不使用 50% 叠加图、参考图哈希或多轮裁剪作为门禁证据。
- 绝对差异热力图只能筛选候选区域，不能单独判定还原度。

## 必查维度

### 版式

- 标题、副标题、标签、正文框、页码和结构区的位置、尺寸、对齐与留白。
- 主要元素之间的垂直节奏、左右边距和视觉基线。

### 构图

- 主视觉的尺度、位置、裁切、朝向和画面重心。
- 前景、中景、背景的比例与页面平衡。

### 层级

- 标题、正文、标签和主视觉的视觉主次。
- 阅读顺序是否与参考图一致。
- 对象前后遮挡关系是否符合设计目标。

### 色彩与质感

- 主色、强调色、背景明暗、透明度和整体氛围。
- 允许渲染差异，但不能出现明显变色、灰度或对比度偏离。

### 边缘融合与视觉过渡

- 图片与背景、人物与环境、明区与暗区之间的渐隐方向、宽度、纹理和光晕是否与参考图一致。
- 检查素材裁切边界是否形成明显矩形接缝、色带、亮度跳变或纹理突然中断。
- 简单规则渐变可以使用原生形状；复杂氛围过渡应按 `visual-transition-strategy.md` 使用透明图片、无字底图或混合方案。
- 文字可读且对象位置正确，仍不能抵消明显的边缘融合失败。

### 字体观感

- 字体、字号、粗细、颜色、行距、换行和文字块宽度。
- 正确文案优先于 AI 参考图中的错误字形。

### 关键素材

- 人物、截图、证据图、作品图和品牌元素没有缺失、错换或明显失真。
- Mode B/C 的可编辑边界和分层要求同时满足。

## 偏差级别

- `blocker`：错页、缺失关键模块、增加未经授权内容、核心素材身份错误或整体构图完全错误。
- `major`：位置、尺寸、裁切、层级、颜色、字体观感、间距或边缘融合出现一眼可见的明显偏差，影响页面设计意图；明显矩形接缝和错误渐变方向属于此级别。
- `minor`：不影响内容、层级和整体观感的轻微差异。

## 通过条件

### Mode B

- `visualFidelityStatus = PASS`。
- `majorFidelityDeviationCount = 0`。
- `visibleAssetSeamCount = 0`。
- 每页标题、正文、标签、结构区和背景主视觉达到参考图目标。
- 允许背景与主视觉合成，但合成后的构图和色彩仍需达标。
- `minor` 偏差必须逐页记录；不能用“可编辑”解释明显的视觉降级。

### Mode C

- 满足 Mode B 的全部要求。
- 背景、人物、内容图、文字和结构分别达到参考图中的位置、尺度、层级和视觉作用。
- 分层后不能因素材拆分导致构图、边缘融合或整体氛围明显退化。

## 审计输出

总报告至少包含：

- `visualFidelityStatus`
- `majorFidelityDeviationCount`
- `minorFidelityDeviationCount`
- `fidelityFlaggedPages`
- `visibleAssetSeamCount`
- `transitionFlaggedPages`
- `visualTransitionByPage`
- `visualFidelityByPage`
- 参考图目录、最终渲染目录和 pairing manifest
- 审计者或模型结论、人工证据和 `needsHumanReview`

每个偏差至少记录：

- `page`
- `dimension`
- `element`
- `severity`
- `referenceObservation`
- `renderObservation`
- `evidence`
- `recommendedFix`
- `status`

若模型连续两轮对同一视觉偏差结论矛盾，设置 `needsHumanReview = true`，由人工决定是否达到参考图目标。
