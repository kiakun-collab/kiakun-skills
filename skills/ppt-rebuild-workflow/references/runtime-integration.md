# Runtime Integration

本 Skill 负责模式选择、语义校验、资产策略、可编辑边界和增强 QA，不另行定义底层 PPTX 构建运行时。

## Presentations Skill 激活时

- 构建、导入、编辑、导出和渲染遵循 `presentations:Presentations` 的 artifact-tool presentation JSX 契约。
- 不默认使用 `python-pptx`、直接 OOXML 或 LibreOffice 修改最终 PPTX。
- 本 Skill 的三个脚本只读 PPTX 包，不替代构建、导出或渲染运行时。
- 渲染优先使用 Presentations Skill 提供的 artifact-tool helper。
- `acceptance_renderer` 默认记录为 artifact-tool render；如果用户最终要求 PowerPoint desktop fidelity，必须记录 renderer delta，不能把 artifact-tool 渲染视为 PowerPoint 原生完全一致。
- Mode B/C 可用 artifact-tool 生成临时参考校准 deck/page；最终交付 deck 必须排除整页参考校准层。
- QA 临时产物在验证期间保留；最终保留、清理和交付遵循用户要求及 Presentations Skill。

## 参考图重构的优先契约

当本 Skill 以 Mode B/C 重构幻灯片截图、image-only PPTX 或 AI 参考图时：

- 参考图是忠实重构目标，不是要求改进的 `quality reference`。
- 验收目标是达到参考图约定的版式、构图、层级、色彩、字体观感和关键素材效果，不得要求超越参考图。
- 不适用 Presentations 通用新建流程中的 `beat the reference`、`comeback rubric` 或同类改进要求；若其报告结构要求填写该指标，记录 `reference delta = n/a`。
- Presentations 仍负责 artifact-tool 构建、导入、导出和渲染；本 Skill 的视觉还原度规则负责判定重构是否达标。
- 只有用户明确要求“改版、优化、升级或做得比参考图更好”时，才允许创建新的设计目标。先进入 Mode D 生成并确认新参考方向，再按 Mode B/C 重构。
- 正确修复 AI 伪字、乱码或事实错误不属于未经授权的重新设计。

## 独立运行时

- 先探测当前环境可用的构建和渲染能力，再选择实现。
- 不假定 PowerPoint COM、LibreOffice 或其他外部渲染器存在。
- 无渲染器时继续执行只读包内审计，并把视觉 QA 标记为未完成或降级，不能声称完整 Level 2/3 通过。

## 工具权限

- 子 Agent 只在当前平台允许且用户明确授权时使用。
- Skill 文档不能越过当前线程的工具、权限、审批或清理策略。
