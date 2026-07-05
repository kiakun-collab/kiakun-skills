# Level 3 Delivery Checklist

- [ ] Level 2 全部通过。
- [ ] `coordinateCalibration.status = PASS`，临时校准层已验证，最终 deck 未包含整页参考图。
- [ ] 参考图与渲染图并排证据已检查。
- [ ] 纯图片基线 deck 已渲染为 `baseline-render/`（同后端同画布）；分层编辑版还原度已同时对照原始参考图与 `baseline-render/`，基线对照通过。
- [ ] `visualFidelityStatus = PASS` 且 `majorFidelityDeviationCount = 0`。
- [ ] 分层后的版式、构图、层级、色彩、字体观感、间距和关键素材达到参考图目标。
- [ ] 每个分层对象有视觉抽取、资产审计或原 PPTX 来源；低置信对象已闭环。
- [ ] 主要文字样式有 typography calibration 记录；字体候选在同一 `acceptanceRenderer` 中比较，最终 bbox、baseline、lineCount 和 overflow 证据完整。
- [ ] 首次构建记为 `autoIterationCount = 0`，返修次数不超过 3；任何自动降级或 `autoFidelityBlocked` 都已记录，存在阻断项时未声明 Level 3 通过。
- [ ] `wholeReferenceImageEmbedded` 有自动风险证据、人工对照结论和最终状态。
- [ ] `combinedBackgroundPersonPictureCount` 有自动证据、人工证据和最终状态。
- [ ] `contentPicturesAreIndependentObjects` 有自动证据、人工证据和最终状态。
- [ ] `visualOverlapCount` 有自动证据、人工证据和最终状态。
- [ ] `visualExtractionComplete` 有自动证据、人工证据和最终状态。
- [ ] `typographyCalibrationComplete` 有自动证据、人工证据和最终状态。
- [ ] `forbiddenOverlayShapesDetected` 有自动证据、人工证据和最终状态。
- [ ] 所有不可拆分例外已写入 asset-audit。
