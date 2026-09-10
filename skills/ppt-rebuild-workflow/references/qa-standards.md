# QA Standards

QA 等级定义交付边界，executionProfile 定义校准成本。fast / balanced 不降低文案、可读性或还原度门槛；strict 增加完整计算证据。旧报告未声明 profile 时继续严格验证，不能因升级静默放宽。

## Level 1 快览

Mode A：页数与页序正确、媒体无空文件、PPTX 可读，检查 contact sheet。明确每页整图、不承诺编辑文字。无需 B/C 抽取、字体探针、坐标校准。

## Level 2 可编辑重构

- task-input、逐页 visual-extraction、layout-spec 保留实际来源；可共享 style-spec。
- 用户定稿覆盖的文字免于截图识别复核，以导出原生文字对照定稿；未覆盖部分按 text-recovery 核对。textRecovery.unresolvedItems 未清空时内容未通过，数字、专名和否定词不能猜。
- audit_pptx_structure.py 与 audit_pptx_text_frames.py 运行成功，保留报告。检查实际 PPTX、页数、媒体、字体槽位及继承、可编辑文字与约定结构。
- 大图覆盖风险必须结合资产身份复核。wholeReferenceImageEmbedded 有自动风险证据与对照结论，不能仅凭覆盖率判断。
- 未解析字体、对象来源、几何变换、必须编辑冲突逐项闭环。文本框相交先辨识实际字形与设计意图，不机械拆散连续标题；有意的 shape/image 叠放不纳入通用碰撞门禁。
- 保留 `textFrameIntersections` 原始计数。确实无可见文字重叠时，用 `geometryExceptions` 按 page、intersectionIndex（从 0 起）逐项记录 reviewer、reason、renderObservation、status=NO_VISIBLE_TEXT_OVERLAP；引用绑定当前 PPTX 的实际 text-frame-audit。漏项、重复项、过期报告均不能通过，不手工清零。
- make_reference_render_comparison.py 或等价配对产物校验页码、缺失、重复和多余页，保留 pairing manifest。
- 一次整页优先的最终 PNG 对照分别记录文字可读性、版式、构图、层级、色彩和主要素材。不得把多轮裁剪作为默认审计流程。
- visionAuditStatus = PASS、visualOverlapCount = 0、visualFidelityStatus = PASS、majorFidelityDeviationCount = 0、visibleAssetSeamCount = 0。两项视觉结论可在同一次复核、同一个报告中，不要求重复看两遍。
- 不要求像素级完全一致；minor 逐页记录，不强制为细微差异继续返修。普通叠放虽不碰文字，明显偏离参考图仍可能构成视觉还原度偏差。
- 用户要求统一模板时，以共同模板参数和逐页内容要求为验收目标，AI 参考图非意图性偏差的归一化不计失败。真实观测与期望模板参数分开保留，公共模板校准一次，最终逐页检查可读性、内容与必要布局例外。
- autoFidelityBlocked = false、未解决必须编辑冲突为 0 才能通过。修复后必须用新渲染验证，只有共享组件改变时扩大到相关页。

### 校准证据

fast / balanced：每页 renderVerificationFile 记录真实观察、坐标与文字验证状态，渲染路径匹配 pairing manifest；outputPptxSha256 和各页 renderSha256 绑定实际文件，哈希仅防旧证据误用，不证明视觉质量。无专项需要时 coordinateCalibration.status = NOT_REQUIRED 并写理由。triggeredChecks 中有坐标/字体触发项则提供相应计算脚本 PASS 产物，不能只写“已检查”。

strict：逐页 measurements 与标注图，coordinate-calibration 脚本 PASS，主要样式 typography scoring PASS；少于 3 个稳定锚点 INCONCLUSIVE，不能虚构。临时校准层仅在诊断需要时创建。

validate_rebuild_evidence.py 检查文件引用、上述校准证据与状态；它不能代替真实看图，也不会自动证明模型填写的观察正确。

## Level 2 可选增强

风险标注图、精确对齐后差异热力图、独立审计者只在可解决具体疑点时增加。热力图只筛选区域，不独立决定 PASS/FAIL。

## Level 3 完全分层

Level 2 全部通过，并验证用户约定范围内的背景、人物、内容图各自独立及可编辑结构。独立对象和合成人物计数按已要求拆分的资产范围检查，未要求拆分的场景内部人物不计为违规。全分层不自动强制 strict；普通图可用 renderVerification 完成坐标和字体验证。

level3Gates 逐项记录 automatedEvidence、manualEvidence、status。manualEvidence 是实际视觉复核，不必等用户逐对象确认。包含 wholeReferenceImageEmbedded、combinedBackgroundPersonPictureCount、contentPicturesAreIndependentObjects、visualOverlapCount、visualExtractionComplete、typographyCalibrationComplete、forbiddenOverlayShapesDetected。这里 typographyCalibrationComplete 包括通过的最终渲染验证或按需计算探针，不强制每页候选搜索。例外必须已经在编辑范围内获允许。

`assetAuditFile` 必填，覆盖用户指定独立资产及 alpha 资产 ID。验证真实图像通道、可见主体和渲染边缘；独立对象计数、PNG 扩展名或绘制的棋盘格都不能证明透明。允许人工接手时交付 `MANUAL_CUTOUT_REQUIRED`，完整 Level 3 仍未通过。

## Level 4 增量修改

Mode E：源文件备份与哈希、新文件另存、只修改指定对象，保留用户文字/形状/位置。检查变更页前后渲染及对象差异；共享样式改变才扩大范围。新重构区域按 B/C 范围做验证。

Level 1/4 走各自检查表与报告；validate_rebuild_evidence.py 当前只验证 Level 2/3，不拿它的“不适用”当作通过。

## 交付

默认 `deliveryProfile=standard`：outputs 只放最终 PPTX、预览、简短交付说明和需用户处理的素材；详细对象、审计与版本日志保留 work。`benchmark` 才额外整理阶段耗时、失败尝试、探针和操作实验的对照报告。两种交付记录量不改变内容、视觉和编辑边界标准。

内容、视觉、编辑范围、证据合规分别报告；轻微差异可记录在已通过的视觉复核中，待抠素材不能假称完整分层。由公共脚本组合真实统计与一份视觉复核，不为缩短说明丢弃证据，不把字段缺失写成 PASS。预览失败时 PPTX 可先交付，但视觉 QA 必须记未完成。
