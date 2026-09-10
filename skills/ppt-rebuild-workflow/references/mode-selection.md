# Mode Selection

## 先拆开三个问题

1. 工作对象：operation = incremental | rebuild。用户要求保留当前 PPTX 继续修改时选 incremental；“已有 PPTX”本身不是增量条件，整套重做仍是 rebuild。
2. 设计意图：redesignRequested 仅在要求新构图、新风格、新设计时为 true。“优化识别/速度/还原度”、错字、OCR 不确定均为 false。
3. 编辑范围：deliverable = preview | editable | layered。preview 需用户明确只要看图/整页图；editable 默认；layered 用于明确要求全部分层、人物背景分开等。

理解肯定、否定、约束和范围，记录 intentEvidence 原话。不要用“快”“优化”“全部”单关键词路由。之后用 resolve_rebuild_route.py 固定决策；脚本不负责自然语言识别，不得把推测伪装成明示要求。

实际任务用 `rebuild_workflow.py init` 在构建前保存不可变路由快照。后续步骤检查任务与路由未被改写；用户改变需求时建立新的运行记录。只做预览也不绕过该轻量入口。

分层范围使用 `editableBoundary.mustRemainIndependentImages` 和 `mustHaveAlpha` 记录实际资产 ID。只点名一个人物时仅该对象升级分层，不顺带拆全部烟雾、玻璃、照片内部对象。缺少干净素材影响 assetStrategy，不改变设计意图或自动变 D。提供标题/正文也不改变路由，只改变文字来源。

## 决策与组合

- incremental 且有当前 PPTX：Mode E；只在指定范围实现 editable/layered 目标。局部改版可以在 E 内加设计阶段。
- rebuild + 明确新视觉方向：Mode D 为设计阶段，记录后续 A/B/C 目标。只要参考图则停止于 D。
- preview：Mode A，一页一图，Level 1。
- editable：Mode B，文字、表格、主要结构可编辑，Level 2。
- layered：Mode C，B 基础上人物、背景、内容图独立，Level 3。照片内部像素并不变成矢量图。

E 是修改策略，D 是设计阶段，B/C 是编辑范围，不再互相吞掉。E 的 Level 4 验证保留原文件和修改范围；重构区域仍检查对应编辑范围。

## 速度与 QA 分开

executionProfile = fast | balanced | strict：默认 balanced；明确“尽快”可选 fast；明确要求精确测量/逐项严格校准用 strict。“正式交付”或“全分层”本身不强制 strict。

快不能覆盖必须可编辑要求；“先给我看看”不能把最终可编辑需求降成 A，除非明确接受这一轮图片预览。模式不能由 QA 等级反推。

## 典型用例

| 用户要求 | 结果 |
| --- | --- |
| 图片转 PPT，没有补充 | B + balanced |
| 尽快重构，文字还能改 | B + fast |
| 人物背景分别可移动 | C |
| 不用可编辑，原图装进 PPT 就行 | A |
| 修正错字，布局照旧 | B，局部恢复文案 |
| 优化识别准确率，忠实还原 | B，风险复核，非 D |
| 已手改 PPT，只换背景 | E |
| 已有 PPTX，但全部重新设计 | D → B/C |
| 保留改稿，只拆第二页人物背景 | E，第二页按 C 范围验收 |
| 重新设计封面，你自行定稿并做 PPT | D → B，不强制选图 |
| 给三种参考图，我来选 | D，等待选择 |

缺少增量源文件或当前预览范围与可编辑承诺冲突时，解决真实冲突。已有源文件、授权与偏好在会话中持续有效。
