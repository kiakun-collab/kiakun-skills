---
name: ppt-rebuild-workflow
description: Use when rebuilding slide screenshots, image-only PPTX files, AI-generated reference slides, or user-edited PowerPoint drafts into editable PPTX deliverables.
---

# PPT Rebuild Workflow

把参考画面重构成符合用户编辑需求的 PPTX。默认忠实重构，先构建可用初版，再根据实际问题定向校准。

## 默认执行

只发一张图并说“转 PPT / 重构”：默认 **Mode B + balanced + Level 2**，文字、表格与主要结构可编辑，复杂主视觉可合成图片。直接说明边界并开始，不要求用户填写模式、QA、字体、输出名。只有真实需求冲突或关键内容缺失才提问。

1. 读 [mode-selection.md](references/mode-selection.md)，从用户原话提取意图。按 [execution-runner.md](references/execution-runner.md) 先运行 `rebuild_workflow.py init` 固定路由，再启动构建；不在交付前补跑。
2. 用户明确提供的标题、正文直接作为该范围的定稿，不对照图片重新识别、纠错或要求确认。其余文字按 [text-recovery.md](references/text-recovery.md) 处理；图片仍提供对象 bbox、样式与层级。文案较原图变长时调整文本框/换行，不删改定稿。
3. 保存最小任务记录与逐页抽取，再用一份统一 `layout-spec` 驱动构建，见 [data-driven-build.md](references/data-driven-build.md)。公共样式和模板定义一次，每页只写内容与差异；展开布局与 QA 兼容文件由程序生成，不重复手填。按 [visual-extraction-pass.md](references/visual-extraction-pass.md) 保留实际观测，不倒填测量。
4. 保存 PPTX 后用同一 acceptanceRenderer 渲染。包内与几何审计可并行；一次逐页视觉复核分别记录文字可读性与参考图还原度双门禁。
5. 只修有证据的问题，只重渲染受影响页；达到门槛即停止。按 [qa-standards.md](references/qa-standards.md) 验证。公共脚本汇总实际审计和同一份视觉复核；默认交付成品、预览、简短未完成清单，详细证据留在 work/。

## 不变边界

- 内容优先级：用户本次明确给出的定稿 > 当前 PPTX/业务原文 > 图中清晰文字。只在提供范围内覆盖；用户仅给标题时，不视为正文也已提供。最终检查导出文字与定稿一致、没有漏字和溢出，免去的是重复识别，不是排版验收。
- Mode B/C 不得要求超越参考图。改版需要用户设计意图；纠正错字不自动转 D。
- 用户明确要求统一模板时，以共同模板约束为准，归一化 AI 参考图中的非意图性样式与位置偏差；保留内容需要的布局变化，不额外转 D。未要求统一或要求严格逐图还原时保留逐页差异。验收使用相同依据，不追求零像素误差。
- 承诺可编辑的文字和结构必须保持可编辑。复杂视觉只在已约定边界内使用独立图片或 baked-asset；不能为通过 QA 偷降级。
- 除 A 外整页参考图不得嵌入成品。纯色用背景填充，规则结构用原生形状；最终形状进入 `visual-extraction.shapes[]` 并保留来源。
- 默认坐标系为 1280 x 720；非 16:9 自动保持原比例，按目标画布建立唯一坐标映射。尺寸要求确实冲突才询问，不能静默拉伸。
- 字体未指定时选本地支持该语言的字体，第一版直接验证；仅风险样式比较候选。
- executionProfile 控制成本，qaLevel 控制编辑范围验收。首次构建为第 0 轮，fast / balanced / strict 默认最多返修 1 / 2 / 3 轮。预算耗尽不等于通过。
- 分层范围落实到对象 ID。生成素材收到后立即检查实际 alpha；默认首次不透明即交付待抠素材和可替换独立对象，继续其余页面，不逐个为透明通道反复重生。用户明确要求自动完成抠图时保留未完成状态并采用合适的抠图路径。见 [asset-policy.md](references/asset-policy.md)。
- 素材生成与文字/图表结构搭建交错进行，独立页按就绪顺序构建；不等待所有困难素材重试完毕才出初版。详见 [adaptive-verification.md](references/adaptive-verification.md)。

## 按需加载

| 需求 | 文件 |
| --- | --- |
| A 整页图预览 | mode-selection.md；Level 1 |
| B 文字及主要结构可编辑 | [semi-editable-workflow.md](references/semi-editable-workflow.md) |
| C 主视觉也独立分层 | [full-layered-workflow.md](references/full-layered-workflow.md) |
| D 用户要求新视觉方向 | [mode-d-workflow.md](references/mode-d-workflow.md) |
| E 修改用户当前 PPTX | [incremental-edit-workflow.md](references/incremental-edit-workflow.md) |
| 新建重构页、统一数据或批量模板复用 | [data-driven-build.md](references/data-driven-build.md)：统一坐标、模板合并和 Presentations 适配器 |
| 没有干净底图、需要抠图/分层 | [asset-policy.md](references/asset-policy.md) |
| 复杂背景中的人物/产品需保留原貌并独立 | [辅助分割方法](references/assisted-cutout.md)：粗轮廓 + GrabCut，限定局部修正次数 |
| 高精度要求或已发现位置/字体偏差 | [autonomous-calibration.md](references/autonomous-calibration.md) |
| 复杂光晕、渐隐、图片融合 | [visual-transition-strategy.md](references/visual-transition-strategy.md) |
| 构建细节/异常 | [implementation-guardrails.md](references/implementation-guardrails.md) |
| 具体视觉疑难 | [visual-overlap-qa.md](references/visual-overlap-qa.md)、[visual-fidelity-qa.md](references/visual-fidelity-qa.md) |

不要开场加载全部模式、QA 子文档和模板。同一任务的派生记录从同一份抽取数据生成，避免重复填表。

## 运行时与失败处理

实际制作读 [runtime-integration.md](references/runtime-integration.md)。Presentations 激活时构建和渲染遵守其当前契约，本 Skill 补充边界与 QA，不重复视觉评分。其他重构 skill 的占位图、强制询问字体等默认值不得覆盖已确定的用户需求。

普通权限下先创建输出目录，使用新版本文件；先保存 PPTX 再渲染。预览失败时继续包内 QA，报告视觉验收未完成。保留用户当前文件；权限与清理遵循当前线程规则。

## 工具与记录

命令与字段见 [script-output-contracts.md](references/script-output-contracts.md)。

- resolve_rebuild_route.py：结构化意图的确定性路由，不靠关键词猜意图。
- assets/runtime/layout-data.mjs、build-from-layout.mjs：解析公共模板与逐页差异，用当前 Presentations 构建；超出能力的对象显式扩展，不静默降级。
- audit_pptx_structure.py、audit_pptx_text_frames.py：只读结构与几何预检。
- extract_reference_measurements.py：批量/精确测量时使用；普通单页可记录实际观察的 bbox。
- calibrate_reference_render.py、score_typography_candidates.py：仅升级校准页/样式，或 strict。
- make_reference_render_comparison.py：按页码配对。
- validate_rebuild_evidence.py：文件、来源与按 profile 选择的证据门禁。

`rebuild_workflow.py` 是日常入口：init / preflight / assets / bind-copy / run / prepare-review / report。任务记录用 [task-input-template.json](assets/templates/task-input-template.json)；审核填写一份 prepare-review 生成的待审文件，再用 [evidence-input-template.json](assets/templates/evidence-input-template.json) 汇总。完整 qa-report 模板仅作字段参考，不逐项重复手写。A/E 保留专用验证；Level 2/3 检查表位于 assets/templates/。

仅在平台可用且已获授权时使用子 agent。单页默认不拆多个重复看图的审计者，独立工作参考 [subagent-prompts.md](references/subagent-prompts.md)。
