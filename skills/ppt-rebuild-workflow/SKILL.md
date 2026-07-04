---
name: ppt-rebuild-workflow
description: Use when rebuilding slide screenshots, image-only PPTX files, AI-generated reference slides, or user-edited PowerPoint drafts into editable PPTX deliverables.
---

# PPT Rebuild Workflow

## 核心原则

先判定任务模式，再制作 PPT。不要把“生成一个 PPTX 文件”当成目标；目标是按用户要求在速度、可编辑性、还原度之间选择正确模式，并用渲染和包内 QA 证明结果。

- 参考图是视觉目标，原 PPTX/用户文案是内容事实源；Mode B/C 不得要求超越参考图，除非用户明确要求改版。
- AI 参考图中的错字、乱码和伪字按 [text-recovery.md](references/text-recovery.md) 做有来源的语义重建；不得通过裁剪、放大或视觉猜字替代文案核对。
- Mode B/C 构建前必须完成视觉抽取、自动坐标校准和文字渲染校准；默认加载 [autonomous-calibration.md](references/autonomous-calibration.md) 与 [visual-extraction-pass.md](references/visual-extraction-pass.md)。
- 文字优先使用 PPT 文本框；结构元素优先使用 PPT 原生形状；复杂低置信形状默认 `baked-asset` 或 Mode B fallback。
- 除 Mode A 外，整页参考图只允许在临时校准或 QA 产物中出现，不得嵌入最终可编辑稿。
- `target_font` 未指定时自动建立并渲染比较 `fontCandidateSet`，不要默认阻塞等待人工选字体。
- 默认坐标系为 1280 x 720（16:9），本 skill 的可编辑坐标系只覆盖 16:9。非 16:9 输入按明确降级路径处理，不提供扩展坐标规范：(1) 走 Mode A 整页图，或 (2) 经用户确认后按等比映射进 1280 x 720 画布（留黑边或裁切由用户选）。不得在无降级确认时擅自继续分层重构。
- 构建细则、最终报告字段和常见反例按需加载 [implementation-guardrails.md](references/implementation-guardrails.md)。

## 始终防错

- 先语义验收；若参考图语义或版式方向错误，先转 Mode D，不要先做坐标锁。
- 不得先写 `layout-spec` 再倒填测量；不得把测量候选框当作最终形状清单。
- 最终形状必须进入 `visual-extraction.shapes[]` 并有来源或回退策略。

## 运行时职责

当 `presentations:Presentations` 同时激活时，PPTX 构建、导入、导出和渲染遵循其 artifact-tool 契约；本 Skill 只补充模式、语义、可编辑边界和 QA。图片重构不适用其通用的“超越参考图”评分，完整边界见 [runtime-integration.md](references/runtime-integration.md)。

## 输入确认

先只确认所有模式都需要的最小输入，避免在模式未定时追问 Mode B/C 专属字段：

- `task_mode`：快版整页图 / 半可编辑重构 / 完全分层重构 / 先重做参考图 / 增量修改。
- `reference_images`：参考图目录或逐页图片路径。
- `slide_order`：页序；文件名和画面编号冲突时以用户说明或画面编号为准。
- `qa_level`：Level 1 / 2 / 3 / 4。
- `output_name`：新输出文件名。

模式确定后，再按对应工作流核对这些字段：

- `autonomy_profile`：默认 `auto-calibrated`；仅当用户要求逐对象确认时使用 `human-assisted`。
- `target_font`：目标字体；可为空，此时必须记录自动选择的 `fontCandidateSet`。
- `acceptance_renderer`：用于字体探针、预览和最终视觉门禁的渲染后端。
- `source_pptx`：原 PPTX 或用户已修改 PPTX，若有。
- `source_copy`：原始文案、创意说明、策划稿、术语表或其他可信业务资料。
- `editable_boundary`：Mode B/C/E 需要；哪些对象允许烘焙进图，哪些对象必须可编辑。
- `asset_strategy`：Mode B/C 需要；复用原图、裁切参考图、生成无字底图、人物透明 PNG、内容图独立对象等。
- `visual_extraction`：Mode B/C 需要；逐页视觉抽取文件，构建前必须生成或说明无法生成的原因。
- `overwrite_policy`：默认禁止覆盖。

使用 [task-input-template.json](assets/templates/task-input-template.json) 记录输入。Mode B 和 Mode C 在构建前必须把关键字段落盘；不能只依赖会话记忆。
对话字段使用 snake_case，模板使用 camelCase；完整映射写在模板 `notes` 中。

## 任务模式

先读 [mode-selection.md](references/mode-selection.md) 判定模式，再按表加载对应文件。

| 模式 | 用途 | 必读文件 |
| --- | --- | --- |
| Mode A 快版整页图 PPT | 每页一张完整图，只用于预览和方向确认 | [mode-selection.md](references/mode-selection.md) |
| Mode B 半可编辑重构 | 一张无字底图 + 可编辑文字和结构层 | [semi-editable-workflow.md](references/semi-editable-workflow.md)、[autonomous-calibration.md](references/autonomous-calibration.md)、[visual-extraction-pass.md](references/visual-extraction-pass.md) |
| Mode C 高还原完全分层重构 | 纯背景、人物、内容图、文字、形状全部分层 | [full-layered-workflow.md](references/full-layered-workflow.md)、[autonomous-calibration.md](references/autonomous-calibration.md)、[visual-extraction-pass.md](references/visual-extraction-pass.md) |
| Mode D 先重做参考图 | 参考图语义或版式错误时先生成候选参考图 | [mode-d-workflow.md](references/mode-d-workflow.md) |
| Mode E 用户修改稿增量修正 | 只替换目标对象，保留用户当前文件内容 | [incremental-edit-workflow.md](references/incremental-edit-workflow.md) |

按需条件加载，避免一次性拉入全部散文:仅当 `presentations:Presentations` runtime 激活时读 [runtime-integration.md](references/runtime-integration.md);仅 Mode B/C 构建阶段读 [implementation-guardrails.md](references/implementation-guardrails.md);进入 QA 时读 [qa-standards.md](references/qa-standards.md)、[visual-overlap-qa.md](references/visual-overlap-qa.md) 和 [visual-fidelity-qa.md](references/visual-fidelity-qa.md);仅当页面存在复杂渐隐/边缘融合时读 [visual-transition-strategy.md](references/visual-transition-strategy.md);仅当参考图为 AI 生成或图片源、需恢复错字乱码时读 [text-recovery.md](references/text-recovery.md)。

## 推荐流程

1. 冻结任务边界、输出路径、模式和 QA 等级。
2. 先做语义验收、异常文字恢复和资产策略；若参考图语义或版式方向错误，转 Mode D。
3. Mode B/C 建立自动坐标锁，完成逐页视觉抽取；渲染后必须运行坐标偏移计算和字体候选评分，再生成 `layout-spec` 与 `style-spec`。
4. 构建 PPTX，先保存成品，再用同一渲染后端导出预览。
5. 运行包内/几何审计和最终 PNG 视觉审计，执行文字可读性与参考图还原度双门禁。
6. 首次构建记为第 0 轮，自动返修最多三轮；仍失败时执行最小自动降级，不能标记为完整通过。
7. 交付报告中说明文件路径、页数、字体、媒体、文本对象、形状、自动降级和未完成风险。

Mode B Level 2 交付前逐项完成 [level-2-delivery-checklist.md](assets/templates/level-2-delivery-checklist.md)。
Mode C Level 3 交付前逐项完成 [level-3-delivery-checklist.md](assets/templates/level-3-delivery-checklist.md)。

## 失败降级

本地导出、渲染或预览写入失败时，不要默认请求提权。先用普通权限处理：

- 预创建输出、预览和 QA 目录。
- 改到新的版本目录或临时目录。
- 先保存 PPTX，再尝试渲染预览。
- 如果预览失败但 PPTX 已生成，继续做包内 QA，并把预览失败写进最终报告。
- 如果构建脚本顺序导致预览失败阻塞 PPTX 输出，修改脚本让 PPTX 保存早于预览，或跳过预览并记录失败。

只有用户明确允许提权或当前环境支持审批时，才考虑请求更高权限。

## 子 Agent 协作

仅在当前平台允许且用户明确授权时使用子 agent。子 agent 只做审计、转写、检查和建议；主线程统一合并参数和修改构建脚本。任务模板和边界见 [subagent-prompts.md](references/subagent-prompts.md)。

## QA 必做项

坐标锁、视觉双门禁、禁裁剪猜字三组规则的单一事实源见 [qa-gates.md](references/qa-gates.md)。完整执行按 [qa-standards.md](references/qa-standards.md)；最终报告字段和常见失败反例见 [implementation-guardrails.md](references/implementation-guardrails.md)。

## 模板

可复制 `assets/templates/` 中的模板建立任务输入、任务派发、资产审计、布局规格、样式规格和 QA 报告。

- Mode B 布局参考：[layout-spec-mode-b-example.json](assets/templates/layout-spec-mode-b-example.json)。
- Mode C 布局参考：[layout-spec-mode-c-example.json](assets/templates/layout-spec-mode-c-example.json)。
- 通用布局模板：[layout-spec-template.json](assets/templates/layout-spec-template.json)。
- 视觉抽取模板：[visual-extraction-template.json](assets/templates/visual-extraction-template.json)。
- 字号校准模板：[typography-calibration-template.json](assets/templates/typography-calibration-template.json)。
- QA 报告模板：[qa-report-template.json](assets/templates/qa-report-template.json)。
- 视觉重叠模板：[visual-overlap-audit-template.json](assets/templates/visual-overlap-audit-template.json)。
- 视觉还原度模板：[visual-fidelity-audit-template.json](assets/templates/visual-fidelity-audit-template.json)。
- 资产审计模板：[asset-audit-template.md](assets/templates/asset-audit-template.md)。
- 样式规格模板：[style-spec-template.md](assets/templates/style-spec-template.md)。
- 页面任务模板：[page-task-template.md](assets/templates/page-task-template.md)。
- 全自动校准与门禁：[autonomous-calibration.md](references/autonomous-calibration.md)。
- 示例中的对象按实际页面删减，不能把示例内容原样带入成品。

## 脚本

- `scripts/audit_pptx_structure.py`：包内结构、字体、对象角色和图片风险审计。
- `scripts/audit_pptx_text_frames.py`：文本框、细长形状和几何覆盖风险审计。
- `scripts/extract_reference_measurements.py`：参考图测量候选、坐标变换、自动锚点和标注图。
- `scripts/calibrate_reference_render.py`：匹配参考图与最终渲染锚点，计算真实坐标偏移和校准状态。
- `scripts/score_typography_candidates.py`：测量候选渲染图并自动选择文字参数。
- `scripts/make_reference_render_comparison.py`：参考图与渲染图配对对照。
- `scripts/validate_rebuild_evidence.py`：迁移旧字段并验证产物引用、计算证据和 QA 门禁。
- `scripts/run_pipeline.py`：顶层驱动器，按顺序 subprocess 串联上述脚本并聚合 `pipeline-report.json`（`--steps` 子集、`--stop-on-fail`、缺输入步骤自动跳过）。

命令、参数和输出字段统一见 [script-output-contracts.md](references/script-output-contracts.md)；修改脚本输出时必须同步更新该契约和 QA 模板。

文字可读性审计见 [visual-overlap-qa.md](references/visual-overlap-qa.md)；参考图还原度审计见 [visual-fidelity-qa.md](references/visual-fidelity-qa.md)；复杂渐隐与边缘融合见 [visual-transition-strategy.md](references/visual-transition-strategy.md)。
