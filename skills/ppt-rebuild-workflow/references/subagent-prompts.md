# Subagent Prompts

仅平台可用且已有授权时使用。单页默认主线程完成，不因存在这些模板就派多个重复审计者。优先拆分独立页面/素材处理；参数与构建由主线程合并。

## 独立文案复核

输入原 PPTX、用户文案/术语、参考图以及待确认项。只核对疑点，不重新转写所有已确认内容。普通截图允许一次带上下文放大/OCR；AI 伪字用语义重建优先，不得通过裁剪或放大恢复不存在的正确字。给出候选文字、逐项来源和 unresolvedItems，多解时未经确认不得写成确定文案。不得改写数字、专名与业务关系。

## 视觉抽取

输入整页参考和可用测量/原 PPTX 参数。输出稳定 id、role、bbox、层级、文案来源与素材策略。复用同一 coordinateTransform，不要求预先提供渲染校准 PASS。复杂视觉仅在约定可编辑范围内回退，不能自行降级。

## 一次综合视觉复核

输入当前最终 PNG、参考图、页码配对、已确认文案和对象风险清单。
按整页优先，文字可读性与还原度在同次复核中分别记录。不得把多轮裁剪作为默认审计流程。
参考图是忠实重构目标，不得要求超越参考图，不得奖励未经用户授权的重新设计。
正常 shape/image 叠放不作碰撞判错；位置、尺度、裁切、层级明显错误仍属于还原度问题。

每页返回：
- page、renderPath、reviewer、observations；
- coordinateStatus、typographyStatus；
- visionAuditStatus、visualOverlapCount；
- visualFidelityStatus、majorFidelityDeviationCount、visibleAssetSeamCount；
- triggeredChecks（kind、reason、所需证据），unresolvedItems；
- 对象 ID、问题、证据、严重度、建议修复。

只报告实际观察，不依据生成者“已经修好”的自述填 PASS。几何预警和模型意见都不能单独证明正确。只对未关闭问题或实际变更区域复核；包内统计直接用脚本，不额外派模型复述。
