# Script Output Contracts

修改脚本参数或输出字段时，同时更新本文件、调用代码、QA 模板和回归测试。

## rebuild_workflow.py / rebuild-runtime.mjs

日常公共入口和参数示例见 [execution-runner.md](execution-runner.md)。

- `init task.json --run-dir work/run`：在构建前保存 task-input、route、content-contract 和哈希；E 备份源文件。已有非空运行目录拒绝覆盖。
- `preflight work/run`：只检查配置路径和 Node/Python 子进程；不安装依赖或修改权限。
- `assets work/run manifest.json`：使用 task.assetPolicy.alphaFailurePolicy 审计真实素材，保存 asset-audit.json。
- `bind-copy work/run extraction.json --output locked.json`：用户定稿覆盖对应文字字段，几何不变；未匹配页不动。导出检查通过 userCopy 的 pptxShapeName 或布局 sourceExtractionId/name 映射。
- `run work/run --stage build --pages 1 --revision 0 --cwd DIR [--render-receipt FILE] -- EXECUTABLE ARG...`：shell=False 执行，注入实际配置的 RUNTIME_NODE_MODULES，独立保存每次日志与退出码。超出返修预算拒绝执行。
- `begin/end`：给外部工具保留实际开始/结束时间、页号、次数、产物哈希；无实际调用不能登记成功。每事件一个文件可并行，不共享覆盖旧错误日志。
- `prepare-review work/run --pptx FILE --render-receipt FILE`：验证最终 PPTX/PNG 哈希和全页覆盖，执行实际结构审计，生成一份主观字段为 PENDING 的版本复核表。
- `report work/run evidence.json`：自动合并实际审计、定稿检查、事件统计和同一份视觉复核，生成 qa-report、evidence-validation、delivery-summary。不会补主观 PASS。

正常完成返回 0；检查未通过/待人工处理返回 1；输入、路径、契约错误返回 2。run 的具体子进程退出码在返回的 exitCode 和事件日志中保留。A/E 的 modeSpecificEvidenceFile 使用专用验证，不把 Level 2/3 验证器不适用视为通过。

runtime 适配器调用当前 Presentations finalizer，同步原生表格 owner 与验证参数，再导入实际 final PPTX 渲染。render-receipt 包含 outputPptxSha256、pages[].renderSha256、finalizeMs、renderMs、startedAt、renderStartedAt、completedAt。集成构建传 --render-receipt 时自动产生真实 render 子事件；其时长已包含于父 build，不重复相加。

## audit_image_alpha.py

```powershell
python scripts/audit_image_alpha.py asset-manifest.json --policy manual-handoff --output asset-audit.json
```

manifest.assets[]：唯一 id、page、path、requiresAlpha；需要交接时附 pptxObjectName、targetBBox、source、inferredRegions。输出实际 mode、hasAlpha、alphaMin/Max、透明像素比例与 sha256；status 为 ALPHA_PRESENT/OPAQUE/EMPTY/UNREADABLE，edgeQuality 始终 NOT_REVIEWED。ALPHA_PRESENT 不证明已抠好边缘。

整体 status 为 PASS、MANUAL_CUTOUT_REQUIRED 或 BLOCKED；退出 0/1/2 分别为通道检查完成且无待办、需处理、输入错误。required 策略下缺 alpha 为 BLOCKED；manual-handoff 只把非空 OPAQUE 交接，空图/损坏图仍阻断该素材。该脚本不修改像素、不自动生图。

## audit_pptx_structure.py

```powershell
python scripts/audit_pptx_structure.py input.pptx --output structure-audit.json
```

退出码：

- `0`：审计完成。
- `2`：PPTX 路径不存在。
- 其他非零：包损坏、XML 解析或写入失败。

字体字段：

- `latinFonts`
- `eastAsianFonts`
- `complexScriptFonts`
- `symbolFonts`
- `themeFonts`
- `unresolvedInheritedFonts`
- `fontFamilies`：以上具体字体的合并视图，不包含无法解析的继承项。
- `fontFamiliesMeaning`：固定说明合并语义。

脚本扫描 slide、layout、master 和 theme。主题 token 可解析时归入对应槽位；空主题槽位、未知 token 或文本未显式指定字体且继承链无法确定时进入 `unresolvedInheritedFonts`。该列表非空时不能默认通过字体门禁。

对象与图片字段：

- `shapeRoleCounts`
- `textShapeRoleCounts`
- `nonTextShapeRoleCounts`
- `pictureRoleCounts`
- `unknownRoleNames`
- `unknownRoleNamesByPage`
- `pages[].pictureCoverages`
- `pages[].maxPictureCoverageRatio`
- `fullSlideImageRiskPages`
- `wholeReferenceImageEmbedded`
- `imageOnlyRisk`

单张图片 frame 覆盖画布 90% 以上时，该页进入 `fullSlideImageRiskPages`。`wholeReferenceImageEmbedded.status` 只能表示自动风险或未检测到风险；覆盖率不能证明图片身份，必须结合参考图、资产策略和最终页面做人工对照。

## audit_pptx_text_frames.py

```powershell
python scripts/audit_pptx_text_frames.py input.pptx --output text-frame-audit.json
```

可选参数：

- `--body-min-chars`：长正文候选最小字符数，默认 `45`。
- `--min-overlap-px`：忽略小于该像素阈值的矩形相交，默认 `1.0`。

`pages[]` 和 `totals` 包含：

- `textFrameIntersections`
- `thinShapeTextFrameIntersections`
- `bodyCandidates`
- `connectorCount`
- `directFrameCount`
- `inheritedFrameCount`
- `unresolvedTextFrameCount`
- `rotationAdjustedShapeCount`
- `groupTransformResolvedCount`
- `unresolvedGroupTransformCount`
- `geometryCoverageRisks`

脚本解析 slide 到 layout、master 的 placeholder frame 继承；`frameSource` 区分 `direct` 和 `inherited`。支持 `p:cxnSp`，并对普通 shape 和 connector 的旋转后轴对齐包围盒做预警。未旋转且具有完整 `chOff/chExt` 的组坐标可换算；旋转组、缺失变换或零 child extent 进入 `geometryCoverageRisks`，不能沉默通过。

`graphicFrame` 及形状与图片之间的通用相互碰撞不纳入通用几何碰撞门禁。表格、图表、SmartArt、图片和形状可以有正常设计叠放；遮挡、穿过或挤压原生文字时，按文字可读性门禁处理。即使没有影响文字，对象的位置、尺度、裁切、前后层级或构图明显偏离参考图时，仍可能构成视觉还原度偏差，按 `visual-fidelity-qa.md` 处理。

## extract_reference_measurements.py

```powershell
python scripts/extract_reference_measurements.py reference-dir --output reference-measurements.json --annotated-dir measurements
```

可选参数：

- `--target-width`、`--target-height`：输出坐标系，默认 `1280 x 720`。
- `--fit-mode auto|contain|cover|stretch`：默认 `auto`；比例不一致时自动使用 `contain` 并记录警告。
- `--min-component-area`：保留边缘连通组件的最小像素数，默认 `8`。
- `--max-candidates`：每页每类候选最多数量，默认 `40`。
- `--auto-anchor-limit`：每页自动宏观锚点最大数量，默认 `12`。

输出字段：

- `settings`
- `pages[].image`
- `pages[].originalSize`
- `pages[].coordinateSystem`
- `pages[].scale`
- `pages[].coordinateTransform`：包含 `sourcePxToCanvas`、`canvasToSourcePx` 和 `fitMode`，用于临时校准层与最终 layout-spec 的坐标锁定。
- `pages[].autoAnchors`：包含 `id`、`kind`、`bbox`、`confidence`、`sourceCandidateIds` 和 `validation`，用于自动锚点叠加验证。
- `pages[].anchorQuality`：稳定锚点数量与 `PASS/INSUFFICIENT`；少于 3 个稳定锚点时不得继续声明坐标校准通过。
- `pages[].anchorAnnotatedImage`：仅显示稳定锚点的低噪声复核图；`annotatedImage` 保留全部候选用于诊断。
- `pages[].measurementEngine`：`opencv-numpy`、`numpy-scipy` 或 `python`。
- `pages[].warnings`、`failedPages`：比例风险与逐图失败；单张坏图不终止其余页面。
- `settings.autoAnchorLimit`
- `pages[].dominantColors`
- `pages[].textLineCandidates`
- `pages[].horizontalLineCandidates`
- `pages[].verticalLineCandidates`
- `pages[].regionCandidates`
- `pages[].annotatedImage`

该脚本只生成测量候选、坐标变换和自动宏观锚点，不是最终视觉判断。agent 先校正测量候选并写入 visual-extraction，构建和渲染后再验证 coordinateTransform 与 autoAnchors。临时 overlay 只用于必要诊断。脚本候选不得直接等同于最终形状清单、OCR 结果或字体参数。

## calibrate_reference_render.py

```powershell
python scripts/calibrate_reference_render.py reference-measurements.json render-dir --output coordinate-calibration.json --overlay-dir calibration-overlays
```

脚本对稳定锚点执行局部边缘匹配，优先使用 OpenCV/NumPy，缺失时自动回退；输出 `calibrationEngine`、`anchorMatches[].dx/dy/confidence/offsetPx`、`maxAnchorOffsetPx`、`tolerancePx` 和叠加图。有效匹配不足时为 `INCONCLUSIVE`，偏移超限时为 `FAIL`；只有计算证据完整且全部页面通过时退出码为 `0`。

## score_typography_candidates.py

```powershell
python scripts/score_typography_candidates.py typography-calibration.json --output typography-calibration-scored.json
```

每个候选必须包含 `id`、`renderPath` 和 `renderCrop`。脚本测量 `inkBBox`、行数、行间距、基线代理、裁切和 overflow；行数不符或裁切的候选被拒绝，最终输出 `generatedBy`、`status` 和 `selected.candidateId`。

## validate_rebuild_evidence.py

```powershell
python scripts/validate_rebuild_evidence.py qa-report.json --normalized-output qa-report-v2.json
```

保持 schemaVersion = 2.0，新增可选 executionProfile、calibrationPolicy 与 renderVerificationFile。旧报告缺少 executionProfile 时按 strict 验证，不静默放宽。只支持 Level 2/3；A/E 使用对应 QA，输入 Level 1/4 返回 INVALID。

- strict / full：保留全页测量标注、calibrate_reference_render.py 和 score_typography_candidates.py 计算证据。
- fast 或 balanced / targeted：允许省略无关 measurementAnnotatedImages、typographyCalibrationFiles；必须有 [render-verification-template.json](../assets/templates/render-verification-template.json) 所示逐页真实渲染复核。coordinateCalibration.status = NOT_REQUIRED 表示不要求全量计算校准，reason 必填；触发的专项检查仍必须提供脚本 PASS 结果。
- renderVerificationFile 的 outputPptxSha256 与 pages[].renderSha256 用标准 SHA-256 从最终实际文件计算；路径统一相对于 qa-report 所在目录。哈希只防旧文件证据混用，不证明视觉判断。
- pages[] 与 pairing manifest 同页且同 render 路径，页数完整无重复；每页 reviewer、observations、coordinateStatus、typographyStatus、triggeredChecks、unresolvedItems 必填。
- triggeredChecks[] 为 kind（coordinate/typography）、reason、evidenceFile；evidenceFile 的 generatedBy 必须分别是 calibrate_reference_render.py / score_typography_candidates.py，status 为 PASS。
- 未决文案、人工复核、超出 profile 返修预算、实际视觉/几何门禁失败均不能通过。必须查看最终 PNG，验证器不判断模型观察真实性。
- Level 3 要求 assetAuditFile，覆盖 task-input 中要求独立/透明的资产 ID；验证器重读实际通道和哈希。不透明人工交接不构成 Level 3 PASS。
- task-input 含 userCopy 时，要求 userCopyAuditFile，并重新检查最终 PPTX 的对应原生文字。用户定稿不再与截图旧字比较；只容忍排版换行。
- 非零 textFrameIntersections 可用 geometryExceptions 按 page/intersectionIndex 逐项解释；审计必须绑定当前 PPTX、保留原始计数且无漏项/重复项。未解释的相交或实际可见重叠仍不通过。
- 公共入口的报告检查路由一致性、contentStatus、editableBoundaryStatus 与未完成事件；strict 若有 renderVerificationFile 也检查实际文件绑定。旧 strict 的计算门禁不变。
- 返回 0：已实现的文件/状态门禁通过；1：门禁失败；2：输入/结构/证据无效。不等于软件独立证明全部视觉质量。

旧字段规范化仍写 visualOverlapCount、visionFlaggedPages、autoIterationCount、acceptanceRenderer、coordinateSystem.width/height，并返回 migrationWarnings。

## make_reference_render_comparison.py

```powershell
python scripts/make_reference_render_comparison.py reference-dir render-dir comparison.png
```

可选参数：

- `--width`、`--height`：每侧图片尺寸。
- `--manifest`：当文件名不能可靠提取页码时，传入 `references` 和 `renders` 文件名到页码映射。
- `--pairing-output`：pairing JSON 路径；默认生成 `comparison.pairing.json`。

脚本按页码映射配对，检查无法提取页码、缺失页、重复页和多余页。任一检查失败返回非零，不按排序位置静默配对。成功时生成对照 PNG 和包含实际 `pairings` 的 JSON sidecar。

## resolve_rebuild_route.py

```powershell
python scripts/resolve_rebuild_route.py task-input.json --output route.json
```

输入可为 task-input.routingIntent，或直接的结构化意图对象。字段：
operation（rebuild/incremental）、deliverable（preview/editable/layered）、redesignRequested、referenceOnly、userSelectsDesign、intentEvidence；executionProfile 在 task-input 顶层，sourcePptx 为增量源。

输出 taskMode、targetMode、qaLevel、changedRegionQaLevel、executionProfile、calibrationPolicy、maxRepairIterations、stages、waitForDesignChoice、requiresInput、missingInputs、reason。E 保留目标编辑范围，D 保留后续构建目标。

默认 B/balanced，不读自然语言关键词。模型必须从原话识别否定与任务范围。退出码 0：路由完成；1：缺少增量来源；2：枚举/类型/意图冲突。脚本只读意图，不验证 sourcePptx 是否真是用户最新文件；实际增量流程必须核实路径与身份。

## 仓库兼容入口与性能参数

保留现有共享分析引擎及 CLI，供本 skill 和 html-to-pptx 调用：

- `extract_reference_measurements.py --jobs N`：0 自动选择进程数，1 串行；`--doctor` 诊断依赖；`--verbose` 把进度写到 stderr。
- `calibrate_reference_render.py --verbose`：输出诊断进度。
- 结构审计指定 `--output` 时默认打印紧凑摘要；`--print-json` 可额外打印完整 JSON。文本框审计打印 totals，完整报告写入 `--output`。
- `make_reference_render_comparison.py --allow-missing` 仅用于局部诊断；不能把缺页对照用于全页交付通过证明。默认仍严格检查页码配对。
- `run_pipeline.py` 保留为旧分析流水线兼容入口。其 PASS 仅表示实际执行的步骤成功，跳过步骤不构成完成证据；不能代替最终交付门禁。新任务默认使用 `rebuild_workflow.py` 记录路由、构建、渲染和证据。
