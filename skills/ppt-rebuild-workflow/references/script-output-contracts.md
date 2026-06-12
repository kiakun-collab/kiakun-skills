# Script Output Contracts

修改脚本参数或输出字段时，同时更新本文件、调用代码、QA 模板和回归测试。

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

## make_reference_render_comparison.py

```powershell
python scripts/make_reference_render_comparison.py reference-dir render-dir comparison.png
```

可选参数：

- `--width`、`--height`：每侧图片尺寸。
- `--manifest`：当文件名不能可靠提取页码时，传入 `references` 和 `renders` 文件名到页码映射。
- `--pairing-output`：pairing JSON 路径；默认生成 `comparison.pairing.json`。

脚本按页码映射配对，检查无法提取页码、缺失页、重复页和多余页。任一检查失败返回非零，不按排序位置静默配对。成功时生成对照 PNG 和包含实际 `pairings` 的 JSON sidecar。
