# Script Output Contracts

修改脚本参数或输出字段时，同时更新本文件、调用代码、QA 模板和回归测试。

## audit_pptx_structure.py

```powershell
python scripts/audit_pptx_structure.py input.pptx --output structure-audit.json
```

stdout：无 `--output` 时打印完整 JSON；有 `--output` 时默认只打印紧凑摘要（`slideCount`/`mediaCount`/各计数/`imageOnlyRisk`/`fullSlideImageRiskPages`，完整报告已落盘），`--print-json` 强制打印完整 JSON。

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

`pages[].pictureCoverages` 与 `pages[].maxPictureCoverageRatio` 只落在本脚本的结构审计 JSON（QA 报告经 `auditArtifacts.structureAudit` 引用该文件），无需再复制到 QA 报告顶层字段。

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
- `--jobs`：逐页分析的并行进程数，默认 `0`（取 `min(cpu_count, 页数)`）；`--jobs 1` 强制串行调试。并行与串行输出逐字节一致。
- `--doctor`：打印 `measurement_engine()` 选择与 numpy/scipy/cv2 可用性及慢路径警告后退出（不需要 input/output）。
- `--verbose`：逐页向 stderr 打印进度；stdout 仍只打印最终输出路径。

退出码：

- `0`：至少一页分析成功。
- `2`：全部页面失败（`pages` 为空，逐图错误进入 `failedPages`）。

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

该脚本只生成测量候选、坐标变换和自动宏观锚点，不是最终视觉判断。agent 必须用 rendered calibration overlay 验证 `coordinateTransform` 和 `autoAnchors`，再写入 `visual-extraction`。脚本候选不得直接等同于最终形状清单、OCR 结果或字体参数。

## calibrate_reference_render.py

```powershell
python scripts/calibrate_reference_render.py reference-measurements.json render-dir --output coordinate-calibration.json --overlay-dir calibration-overlays
```

可选参数 `--verbose` 仅向 stderr 打印每页 tolerance 推导与 render/page 数量 warning,不改变 stdout 契约。

脚本对稳定锚点执行局部边缘匹配，优先使用 OpenCV/NumPy，缺失时自动回退；输出 `calibrationEngine`、`anchorMatches[].dx/dy/confidence/offsetPx`、`maxAnchorOffsetPx`、`tolerancePx` 和叠加图。有效匹配不足时为 `INCONCLUSIVE`，偏移超限时为 `FAIL`。退出码：`0` 仅当整体 `status == PASS`（计算证据完整且全部页面通过）；其余情况（`FAIL`/`INCONCLUSIVE`）为 `1`；输入读取或解析错误为 `2`。

## score_typography_candidates.py

```powershell
python scripts/score_typography_candidates.py typography-calibration.json --output typography-calibration-scored.json
```

每个候选必须包含 `id`、`renderPath` 和 `renderCrop`。脚本测量 `inkBBox`、`lineCount`、`lineGapPx`、`baselineProxyPx` 和 `clippingDetected`(裁切);行数不符或裁切的候选被拒绝,最终输出 `generatedBy`、`status`、`failures` 和每项 `selected.candidateId`。退出码:`0` 全部项通过,`1` 存在 `failures`(单个坏 item 记入 failures 不中止整文件),`2` 输入读取或解析错误。

## validate_rebuild_evidence.py

```powershell
python scripts/validate_rebuild_evidence.py qa-report.json --normalized-output qa-report-v2.json
```

新产物使用 `schemaVersion = 2.0`。验证器可读取旧字段并输出 `migrationWarnings`，但规范化输出只写 `visualOverlapCount`、`visionFlaggedPages`、`autoIterationCount`、`acceptanceRenderer` 和 `coordinateSystem.width/height`。退出码：`0` 全部门禁通过，`1` 契约有效但门禁失败，`2` 输入、结构或证据无效。

## make_reference_render_comparison.py

```powershell
python scripts/make_reference_render_comparison.py reference-dir render-dir comparison.png
```

可选参数：

- `--width`、`--height`：每侧图片尺寸。
- `--manifest`：当文件名不能可靠提取页码时，传入 `references` 和 `renders` 文件名到页码映射。
- `--pairing-output`：pairing JSON 路径；默认生成 `comparison.pairing.json`。
- `--allow-missing`：不因缺失/多余页硬失败，缺失一侧渲染灰格占位，pairing entry 追加 `status`（`matched`/`missing`）。默认(不加此开关)行为不变,pairing entry 不含 `status`。

脚本按页码映射配对，检查无法提取页码、缺失页、重复页和多余页。任一检查失败返回非零，不按排序位置静默配对(除非 `--allow-missing`)。成功时生成对照 PNG 和包含实际 `pairings` 的 JSON sidecar。页码提取策略与 `calibrate_reference_render.py` 共用 `_image_common.extract_page_number`(label 优先),同一文件名两脚本映射一致。
