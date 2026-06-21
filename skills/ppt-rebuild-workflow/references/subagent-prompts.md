# Subagent Prompts

## 文字语义恢复和错字检查

````text
只审计文案，不创建 PPTX，不改图。AI 参考图中的错字、乱码和伪字采用语义重建优先，不得通过裁剪或放大恢复。

输入：
- 原 PPTX：...
- 用户原始文案或业务资料：...
- 术语表：...
- 参考图目录：...

任务：
1. 优先从原 PPTX、用户文案或可信业务资料提取准确文字。
2. 标记参考图中的疑似错字、乱码、伪字和异常换行。
3. 结合同页上下文、相邻页、全稿术语和业务逻辑给出候选文字。
4. 有唯一高置信答案时记录推理证据；存在多个合理候选时设置 needsHumanReview，未经确认不得写成确定文案。
5. 说明每页阅读顺序。

输出：
- 每页文案清单
- 恢复状态、候选文字和证据
- 阅读顺序

使用 JSON：
```json
{
  "sourceFiles": [],
  "pages": [
    {
      "page": 1,
      "kicker": "",
      "title": "",
      "subtitle": "",
      "tags": [],
      "body": "",
      "pageNumber": "",
      "textRecoveryItems": [
        {
          "region": "",
          "observedGlyphs": "",
          "resolvedText": "",
          "status": "exact-source",
          "confidence": 1.0,
          "evidence": [],
          "alternatives": [],
          "needsHumanReview": false
        }
      ],
      "readingOrder": []
    }
  ],
  "unresolvedItems": [],
  "needsHumanReview": false
}
```
````

## 参考图视觉抽取

````text
只做参考图视觉抽取，不创建 PPTX，不修改文件。

输入：
- 参考图目录：...
- 可选测量脚本输出：reference-measurements.json
- 可选测量标注图目录：...
- coordinateCalibration / 临时校准层：...
- 目标字体：
- acceptanceRenderer：...

任务：
1. 逐页查看参考图、测量标注图和临时校准层。
2. 使用已有 `coordinateTransform` 和 `autoAnchors`，不要重新发明坐标系，也不要要求用户人工确认大量锚点。
3. 合并或修正候选文本行，输出文字块 bbox、字形 bbox、行数、颜色、对齐、估计字重和候选字号。
3. 识别可编辑结构形状：卡片、标签、边框、分隔线、页码线、正文框、遮罩等，输出类型、bbox、圆角、填充、描边、透明度、阴影、层级和置信度。
4. 识别内容图、人物、背景主视觉的 bbox、裁切和可编辑策略。
5. 记录主要间距：页面边距、标题到副标题、标签到正文、正文框内边距、页码线到画布边缘。
6. 对低置信对象优先设置 `baked-asset` 或 Mode B fallback；只有必须独立可编辑且无稳定实现时才设置 `needsHumanReview`。

输出：
- 只返回符合 visual-extraction-template.json 思路的 JSON。
- 不要输出 PPT 构建代码。
````

## 字号与间距校准建议

````text
只做字号、行距和文本框尺寸校准建议，不创建最终 PPTX。

输入：
- visual-extraction JSON：...
- 目标字体或 fontCandidateSet：...
- acceptanceRenderer：...
- 可选渲染探针目录：...

任务：
1. 对标题、正文、标签、页码等主要文字样式提出 2-4 个候选组合。
2. 每个候选包含 fontFamily、fontSizePt、构建 API 实际单位、fontWeight、lineSpacingPercent、textBoxW/H、paddingPx。
3. 以参考图 textBlockBBox、glyphBBox、行数、行距和内边距为目标，并记录最终渲染 bbox、baseline、wrap 和 overflow。
4. 若没有同一 `acceptanceRenderer` 的渲染证据，只能标为 candidate，不能标为 verified。

输出：
- 只返回 typography-calibration-template.json 思路的 JSON。
````

## 参考图 vs 渲染图视觉审计

````text
只做视觉审计，不修改文件。

输入：
- 参考图目录：...
- 当前渲染图目录：...

重点检查：
1. 字号、颜色、粗细。
2. 标题、标签、正文框、页码的 x/y/w/h。
3. 垂直间距和左右留白。
4. 标签是否单行、正文是否溢出。
5. 背景和主视觉构图是否接近。
6. 对象前后层级、主次关系和阅读顺序是否一致。
7. 人物、截图、证据图、作品图和品牌元素是否缺失、错换或明显失真。

判定：
- 这是视觉 QA 的还原度门禁，不替代文字可读性审计。
- 参考图是忠实重构目标，不得要求超越参考图，不得奖励未经用户授权的重新设计。
- 不要求像素级完全一致，但未经解释的重大视觉偏差必须为 0。
- 普通形状或图片叠放不做机械碰撞判错；若其位置、层级、裁切或构图明显偏离参考图，仍判定为还原度偏差。

输出：
- 只返回符合以下 schema 的 JSON

```json
{
  "visualFidelityStatus": "PASS",
  "majorFidelityDeviationCount": 0,
  "minorFidelityDeviationCount": 0,
  "fidelityFlaggedPages": [],
  "pages": [
    {
      "page": 1,
      "status": "PASS",
      "deviations": [
        {
          "dimension": "layout",
          "element": "title",
          "severity": "major",
          "referenceObservation": "",
          "renderObservation": "",
          "evidence": "",
          "recommendedFix": "",
          "status": "open"
        }
      ]
    }
  ],
  "needsHumanReview": false,
  "humanReviewEvidence": ""
}
```
````

## 最终渲染视觉重叠审计

````text
只审计最终渲染 PNG，不修改 PPTX，不依据对象参数替代视觉判断。

输入：
- 最终渲染图目录：...
- 可选参考图目录：...

逐页检查：
1. 文字字形是否被装饰线、边框、分隔线、标签轮廓、图片边缘或其他文字穿过、遮挡或紧贴。
2. 标题、副标题、标签、正文、页码是否发生视觉相切，或因阴影/描边看起来重叠。
3. 文字是否被高对比背景边缘切割，导致可读性像发生遮挡。
4. 是否存在参数上不相交、但渲染后字形外沿已经碰撞的情况。
5. 区分“文字正常位于底板内部”与“线条穿过字形”等破坏性重叠。

判定：
- 任一破坏性视觉碰撞都使该页 FAIL。
- 全部页面无问题时，visualOverlapCount 才能为 0。
- contact sheet 仅用于初筛；每页必须按整页优先查看全尺寸图。
- 标记页只放大整页检查清晰度、遮挡和裁切；不通过裁剪、放大或 OCR 猜测 AI 伪字的准确内容。
- 不得把多轮裁剪作为默认审计流程，也不得依据切断连续线条、大面积图片或跨区形状的孤立裁剪图下结论。

输出：
- 只返回符合以下 schema 的 JSON

```json
{
  "visionAuditStatus": "PASS",
  "visualOverlapCount": 0,
  "flaggedPages": [],
  "issues": [
    {
      "page": 1,
      "region": "",
      "text": "",
      "conflictingElement": "",
      "severity": "blocker",
      "evidence": "",
      "recommendedFix": "",
      "status": "open"
    }
  ]
}
```
````

## 无字底图残留检查

````text
只检查底图，不创建 PPTX。

检查每张底图是否残留：
- 标题
- 正文
- 标签
- 页码
- 装饰线
- UI 框
- 明显无法解释的文字痕迹

输出：
- PASS/FAIL
- 问题页
- 问题位置和严重度

使用 JSON：
```json
{
  "status": "PASS",
  "pages": [
    {
      "page": 1,
      "residuals": [
        {
          "type": "text",
          "region": "",
          "severity": "major",
          "evidence": ""
        }
      ]
    }
  ]
}
```
````

## 包内 QA 复核

````text
只复核 PPTX 包结构和渲染产物，不修改文件。

检查：
- slideCount
- mediaCount
- emptyMediaCount
- fontFamilies
- textRunCount
- shapeCount
- 是否有整页参考图误嵌入
- 是否有明显冗余文本框或形状

输出：
- 只返回符合以下 schema 的 JSON

```json
{
  "status": "PASS",
  "metrics": {
    "slideCount": null,
    "mediaCount": null,
    "emptyMediaCount": null,
    "fontFamilies": [],
    "textRunCount": null,
    "shapeCount": null,
    "imageOnlyRisk": null
  },
  "failedChecks": [],
  "recommendations": []
}
```
````
