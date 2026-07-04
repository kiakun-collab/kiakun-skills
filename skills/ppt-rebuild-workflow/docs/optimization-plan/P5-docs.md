# P5 · 文档体系与模板(token 经济 + 一致性)

> 来源:文档体系审计。核心发现:Mode B 一条路径实际拉入 ~1,104 行散文(约 85% 的 references 树);
> 坐标锁规则在 8 个文件重复、禁裁剪猜字规则在 ~7 处重复、视觉双门禁在 ~8 处重复。
> **所有文档改动必须保持 `tests/test_mode_selection_contract.py` 通过。**

## P5-1 建立 qa-gates.md 单一事实源 ◐(单一源已建;物理去重暂缓)

> 部分完成(2026-07-05):新建 `references/qa-gates.md` 作为坐标锁 / 视觉双门禁 / 禁裁剪猜字三组规则的**权威单一事实源**,并从 SKILL.md「QA 必做项」引用。这已实现「单一源」目标(agent 有唯一权威处)。
>
> **物理去重(删掉 7 处重复、改为链接)暂缓**,原因:`test_mode_selection_contract.py` 用 assertIn/assertNotIn 把这些规则的**具体字样钉死在具体文件**(如 `整页优先`/`不得把多轮裁剪作为默认审计流程`/`双门禁`/`版式、构图、层级、色彩`/`不要求像素级完全一致`/`majorFidelityDeviationCount = 0`/`仍可能构成视觉还原度偏差`/`语义重建优先`/`不得通过裁剪或放大恢复` 等)。这些被钉住的字样不能从其所在文件移除,可安全删除的只是未被钉住的少量副本。真正的 200-300 行削减需逐条比对每个契约断言、每改一处即跑契约测试,属高风险精修,建议留独立专项。已把 qa-gates.md 作为落点备好。

- 问题: 坐标锁规则(3-12 稳定锚点、<3 ⇒ INSUFFICIENT、coordinateCalibration.status=PASS、临时整页图不得入成品)在 8 个文件近逐字重复:`SKILL.md:14`、`autonomous-calibration.md`、`visual-extraction-pass.md:19-22/79`、`implementation-guardrails.md:18`、`qa-standards.md:37`、`level-2-delivery-checklist.md:4-6`、`page-task-template.md:27-28`、`semi-editable-workflow.md:22`。
- 改动: 新建 `references/qa-gates.md`,收纳三组高重复规则(坐标锁、视觉双门禁、禁裁剪/放大猜字);其余 7 处改为一句话 + 链接。
- 验收: Mode B 路径文档量净减 200-300 行;规则内容零丢失(逐条比对);契约测试通过。

## P5-2 QA 三文档合并评估 ☐(暂缓,保守判定不合并)

> 评估(2026-07-05):`qa-standards.md`/`visual-overlap-qa.md`/`visual-fidelity-qa.md` 被契约测试**分别按文件名钉住多条字样**(见 P5-1),合并会大改引用链且极易触发契约断言失败。按计划「保守执行」条款,判定**不合并**;去重收益已大部分由 P5-1 的 qa-gates.md 单一源承接。若后续要做,建议只在 focused session 内、以契约测试为逐步护栏做「去重不合并」。

- 定位: `qa-standards.md`(117)+ `visual-overlap-qa.md`(102)+ `visual-fidelity-qa.md`(111)= 330 行,重叠严重。
- 改动: 合并为一份 `qa-standards.md`(含 overlap/fidelity 两节);逐冲突检查清单下沉到已镜像它们的 audit-template JSON。**保守执行:若合并导致引用链大改,可只做去重不做合并。**
- 验收: 契约测试通过;SKILL.md 引用链同步更新。

## P5-3 默认加载降级为条件加载 ☑

> 完成(2026-07-05):SKILL.md 模式表下方原「通用运行时边界读 runtime-integration.md…」的无条件链式加载,改为**条件加载**表述:runtime-integration 仅 presentations runtime 激活时、implementation-guardrails 仅 Mode B/C 构建阶段、qa 三件仅进入 QA 时、visual-transition-strategy 仅有复杂渐隐时、text-recovery 仅 AI/图片源需恢复文字时。所有文件名引用保留,契约测试 15 全绿。

- 定位: `SKILL.md:68` 无条件链式加载。
- 改动: `runtime-integration.md`(仅 presentations runtime 激活时)、`text-recovery.md`(仅 AI 参考图/图片源)、`visual-transition-strategy.md`(仅存在复杂渐隐)改为"仅当…时加载"。
- 验收: SKILL.md 对应行改为条件式表述;契约测试通过。

## P5-4 修复 task-input-template 假"完整映射" ☑

> 完成(2026-07-05):`task-input-template.json` 的 notes 首条补全为 **14+ 字段完整 snake_case↔camelCase 映射**(补上 autonomy_profile、target_font、acceptance_renderer、source_pptx、editable_boundary、asset_strategy、visual_extraction、overwrite_policy、permission_policy 等此前缺失项)。JSON 校验通过,契约测试 15 全绿。

- 问题: `SKILL.md:54` 承诺 snake_case↔camelCase"完整映射"在模板 notes 中,实际只映射了 14 个字段中的 6 个(缺 autonomy_profile、target_font、acceptance_renderer、source_pptx、editable_boundary、asset_strategy、visual_extraction、overwrite_policy)——agent 会瞎猜其余 8 个。
- 改动: 补全 `task-input-template.json` notes 的 14 字段完整映射。
- 验收: 14 个对话字段全部有对应 camelCase 模板字段;契约测试通过。

## P5-5 模板字段漂移修正 ☑(e 保留)

> 完成(2026-07-05):(a) `qa-report-template.json` `bodyCandidatesPerPage` → `bodyCandidates`(与脚本一致;grep 确认全仓无其他引用);(b) 在 `script-output-contracts.md` 写明 `pictureCoverages`/`maxPictureCoverageRatio` 只落结构审计 JSON、经 `auditArtifacts.structureAudit` 引用、不必复制到报告顶层;(c) `layout-spec-template.json` notes 补「背景 editable 按模式取值:Mode B=false / Mode C=true」;(d) 同 notes 补 anchorQuality(PASS/INSUFFICIENT)vs coordinateCalibration.status(PASS/INCONCLUSIVE/FAIL)是不同对象不同词表的澄清;(f) `layout-spec-mode-c-example.json` 补 `visualTransitions: []`。(e) `checks{}` 里 reasonableShapes/noRedundantTextBoxes/spacingCloseToReference 等经 grep 确认全仓仅此模板引用,判定为**有意的人工 QA 占位项予以保留**(不删,避免削减人工核对信号)。所有 JSON 校验通过,契约 15 全绿。

- 修正:
  - (a) `qa-report-template.json:36` `bodyCandidatesPerPage` vs 脚本实际输出 `bodyCandidates`(`script-output-contracts.md:60`)→ 统一(建议改模板)。
  - (b) 脚本的 `pages[].pictureCoverages`/`maxPictureCoverageRatio` 在 QA 报告模板中无落点 → 补字段或文档说明不需落报。
  - (c) `layout-spec` 的 `editable` 标志:Mode B 背景 `false`、Mode C 背景 `true`,规则合理但无文档 → 在 implementation-guardrails 或 layout-spec 模板 notes 里写明按模式取值规则。
  - (d) anchorQuality(PASS/INSUFFICIENT)与 calibration status(PASS/INCONCLUSIVE/FAIL)是不同对象的不同词表 → 在 qa-gates.md(P5-1)中一句话澄清,防 agent 混淆。
  - (e) `qa-report-template.json:98-129` `checks{}` 里 `reasonableShapes`、`noRedundantTextBoxes`、`spacingCloseToReference`、`typographyMetricsByPage`、`shapeRolesByPage` 等字段无任何文档/脚本引用 → 删除或补文档。
  - (f) `layout-spec-mode-c-example.json` 缺基础模板中的 `visualTransitions` 数组 → 补齐示例。
- 验收: 模板↔脚本↔契约文档三方字段一致;契约测试通过。

## P5-6 非 16:9 声明降级(D1 已定:仅支持 16:9)☑

> 完成(2026-07-05,方案 b):SKILL.md 核心原则里删除「必须先确认扩展坐标规则」的悬空要求,改为明确声明——可编辑坐标系只覆盖 16:9(1280×720),非 16:9 输入按 (1) Mode A 整页图 或 (2) 用户确认后等比映射进 1280×720(留黑边/裁切) 两条降级路径处理,不做扩展坐标规范。mode-selection.md 的「## 模式边界」新增「坐标系与比例」一节同步。保留契约测试要求的 `默认坐标系为 1280 x 720` 与 `非 16:9` 字样,15 全绿。

- 问题: `SKILL.md:18` 要求非 16:9 任务"先确认扩展坐标规则",但没有任何文档给出规则本身;模板全部硬编码 1280×720 —— agent 必然卡死或擅自降级。
- 改动(执行方案 b): 修改 `SKILL.md:18` 为明确声明:本 skill 坐标系仅支持 16:9(1280×720);非 16:9 输入的处理路径为 (1) 走 Mode A 整页图,或 (2) 经用户确认后按等比映射进 1280×720 画布(留黑边/裁切由用户选),不做扩展坐标规范。删除"必须先确认扩展坐标规则"的悬空要求,mode-selection.md 同步一句话。
- 验收: agent 遇到 4:3 输入时有明确可执行路径,不再卡死或擅自声明支持;契约测试通过。

## P5-7 字体候选种子规则 ☑

> 完成(2026-07-05):`autonomous-calibration.md` 的「字体渲染探针」新增「字体候选种子」小节——给出中文正文/中文标题/西文正文/西文标题 × 无衬线/衬线 的默认种子表,加三条筛选规则(衬脚定衬线列、标题就近取粗字重、中西文各取一套分别指定 eastAsian/latin)。agent 无 `target_font` 时可零提问建候选集。顺带修正该文件 `overflow` → `clippingDetected` 的字段漂移。

- 问题: `target_font` 为空时文档只说"自动建立 fontCandidateSet 并选最低误差",但没说**用哪些字体家族做种子**——开放决策点。
- 改动: 在 `autonomous-calibration.md` 给出默认种子表(中文正文/中文标题/西文各 2-3 个常见系统字体)+ 按参考图文字特征(衬线/非衬线/粗细)筛选的规则。
- 验收: agent 无 target_font 时可零提问完成候选集构建。
