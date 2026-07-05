# M2 · 变换层(extraction.json → layout-spec.json) ✅

> 完成(2026-07-05):`scripts/build_layout_spec.py`(纯 Python)。角色分类(text/shape/image/svg/table/structural)、同 bounds shape 合并(样式合成:fill+line+shadow+radius)、structural 容器丢弃但子元素记 groupId(最近含≥2 产出的祖先)、可表达性评分(backdrop-filter/conic/多层/inset 阴影/svg → baked+bakedReason;baked 登记 pendingBake)、文字专项(runs→sizePt、padding 实测、textLayoutBudget、pre 换行)、fontMap(installed 命中 1.0 / web 映射 0.8+warning / 兜底 Arial 0.5+warning)、cleanliness ratio(>1.3 warning)。`tests/test_transform.py` 10 测试全绿(三层合并为 1、wrapper 不产出+分组、backdrop/多层阴影 baked、字体三档、ratio、旋转用未变换盒)。M1→M2 端到端冒烟通过(html/body 页底合并去重)。
>
> 增强(2026-07-05,吸收实战复盘):fontMap 改为**枚举本机注册表真实字体名**(`load_installed_fonts`),并对拼写/空格差异自动校正(`腾讯体W7`→`腾讯体 W7`,confidence 0.9)、无匹配时明确 fallback 风险警告;`warnings` 新增**超出 1280×720 出界检测**(底部越界预警)。

产出:`scripts/build_layout_spec.py`(纯 Python,无浏览器/COM 依赖,100% 可单测)。
**这是"干净整洁"目标的实现处,是本 skill 的差异化核心。**

## 三个管线阶段

### 1. 角色分类(role classification)

每个元素判定为:`text` / `shape`(有可见背景/边框/阴影的盒)/ `image` / `table` / `svg` / `baked-candidate` / `structural`(纯布局容器,不产出对象)。
判定规则:画了东西才算数——无背景、无边框、无阴影、无文字的元素 → `structural`。

### 2. 扁平化与整洁(cleanliness pass)

- 同 bounds(±2px)嵌套盒合并:样式合成到一个形状(外层背景+内层边框等)
- `structural` 容器丢弃,但语义分组保留:同一容器下的子元素在 layout-spec 中记 `groupId`(M3 生成 PPT group)
- 零尺寸/完全被不透明兄弟覆盖且自身无文字的元素剔除
- z-order 直接采用 M1 的 `paintIndex`
- **整洁度指标**落盘:`cleanliness: { emittedShapes, visibleElements, ratio }`,ratio > 1.3 时 warning

### 3. 可表达性评分(expressibility scoring)

逐元素打分 → `native` 或 `baked`:
- **native 可表达**:纯色/线性渐变(≤8 stops)/径向渐变(中心对称)、四角圆角、单层 outer box-shadow、实线/虚线边框、透明度
- **必须 baked**:`backdrop-filter`、`clip-path`、`mask`、`mix-blend-mode≠normal`、多层阴影、inset shadow、conic-gradient、canvas、video、复杂 SVG(含 filter/mask 或 path 数 > 阈值)
- 简单 SVG(纯 path/rect/circle 图标):默认 baked,`--svg-as-shapes` 开关尝试原生 freeform(借鉴 dom-to-pptx 的 svgAsVector,风险自担)
- 表格:HTML `<table>` → `table` 角色,M3 出原生 PPT 表格
- 每个 `baked` 判定必须带 `bakedReason` 字段——进最终报告,可编辑度审计用

## 文字专项

- 逐段落一个文本框(不是逐行,保可编辑);框 = 段落行盒并集 + 实测 padding
- M1 的逐行几何用于:验证 PPTX 端折行是否一致的**预算依据**(行数、每行宽度),写入 `textLayoutBudget`
- 字体映射:web font-family 链 → 本机已装字体;产出 `fontMap`(源→目标+置信度);无匹配时挑度量最接近的候选并记 warning
- `white-space:pre` / `<br>` → 显式换行;正常折行不写硬换行(编辑友好)

## layout-spec schema(契约,先定稿再动工)

沿用 ppt-rebuild 的 layout-spec 骨架(coordinateSystem/pages/shapes[]),便于 QA 工具即插即用;每 shape:
`id`(=M1 DOM 路径)、`role`、`bboxPx`、`rot`、`fill/line/shadow/radius`、`text{runs,font,align,lineBreaks}`、`groupId`、`zOrder`、`expressibility{verdict,bakedReason?}`。
schema 写入 `references/pipeline-contracts.md` 后冻结。

## 验收

- 纯单测(golden extraction.json → 断言 layout-spec):
  - 同 bounds 三层嵌套合并为 1 形状
  - wrapper div(无视觉)不产出对象但子元素 groupId 正确
  - backdrop-filter 元素 verdict=baked 且 bakedReason 正确
  - 字体映射:已装字体命中 / 未装字体给候选+warning
  - cleanliness ratio 计算正确
- schema 与 contracts 文档一致(契约测试,ppt-rebuild `test_mode_selection_contract.py` 风格)
