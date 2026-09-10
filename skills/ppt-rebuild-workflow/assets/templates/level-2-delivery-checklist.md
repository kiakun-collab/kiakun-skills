# Level 2 Delivery Checklist

- [ ] 来源、页序、模式、executionProfile、编辑范围、字体/渲染器、新路径已记录。
- [ ] 用户定稿已直接采用且导出文字一致；未提供部分已按来源核对，关键未决项为空；没有未经授权的改版。
- [ ] 每页主要对象的 `x/y/w/h` 已从参考图抽取或从原 PPTX 取得，来源与布局引用一致。
- [ ] fast/balanced 的 renderVerification 完整；strict 保存测量 JSON、标注图与全页计算校准。
- [ ] 触发的坐标/字体专项有对应计算证据；未触发用 NOT_REQUIRED 加理由，未伪称 PASS。
- [ ] 包内结构/几何审计完成，未知字体、来源、变换和危险交叠已闭环。
- [ ] 承诺的文字、表格、结构可编辑；整页参考图未进入成品，大图身份风险已核对。
- [ ] 参考/渲染页码配对完整，每页新 PNG 在一次视觉复核中完成双门禁。
- [ ] `visionAuditStatus = PASS`、`visualOverlapCount = 0`。
- [ ] `visualFidelityStatus = PASS`、`majorFidelityDeviationCount = 0`。
- [ ] `visibleAssetSeamCount = 0`，minor 已记录。
- [ ] 返修未超 profile 预算，受影响页已重渲染，必须编辑冲突与 blocker 为零。
- [ ] 输出另存、报告证据与当前 PPTX/渲染绑定，未完成项明确交付。
