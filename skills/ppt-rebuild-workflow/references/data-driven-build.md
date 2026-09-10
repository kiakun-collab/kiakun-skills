# 统一布局数据与模板复用

新建重构页采用一份 `layout-spec.json` 作为构建数据源，坐标继续使用目标画布的 px，字号意图使用 pt。已有观测先保留；从观测和用户要求确定布局，再由公共适配器生成 PPTX。不要同时手写逐页构建代码、完整展开布局和多份同义样式表。

## 模板原则

用户明确要求统一模板时，先整体看同组参考页，确定一次公共背景、页头高度、字体层级、对齐和边距。归一化 AI 出图造成的非意图性小幅偏差；正文结构、图片数量、主体位置和长标题等内容需要的变化仍可逐页调整。沿用 B/C 的编辑边界，这种归一化不额外触发 D。

`templatePolicy.mode` 默认为 `faithful`：按逐图要求还原，仅复用确实共享的部分。用户已明确要求统一模板时用 `normalize`，`basis` 简短记录该要求。相似截图本身不代表用户授权统一样式；已有 PPTX 母版也不因此被重建，Mode E 继续原稿增量编辑。

模板参数来自用户提供的模板，或对整组图片共同设计意图的判断。不要把第 1 页所有参数盲目复制到后续页，也不必机械平均每一处像素偏差。保存实际观测 bbox；期望模板坐标另存在模板里，不把归一化后的坐标倒填成测量结果。

## 最小结构

单页可以只用 `coordinateSystem + background + objects[]`，无需建立模板。多页使用 `pages[]`，需要复用时添加 `styles` 和 `templates`。参见 [空白数据入口](../assets/templates/layout-spec-template.json) 与 [两页蓝白模板示例](../assets/templates/layout-spec-shared-template-example.json)。示例的颜色、字号和坐标不是所有任务的默认视觉风格。

```json
{
  "schemaVersion": "3.0",
  "coordinateSystem": {"width": 1280, "height": 720},
  "templatePolicy": {"mode": "normalize", "basis": "用户要求这组 AI 参考页统一模板"},
  "styles": {"title": {"fontSizePt": 36, "bold": true, "color": "#FFFFFF"}},
  "templates": {
    "blue-white": {
      "background": "#FFFFFF",
      "objects": [
        {"name": "background-header", "type": "shape", "shape": "rect", "x": 0, "y": 0, "w": 1280, "h": 180, "z": 0, "style": {"fill": "#0875ED"}},
        {"name": "title-main", "type": "text", "x": 44, "y": 58, "w": 1180, "h": 66, "z": 10, "styleRef": "title"}
      ]
    }
  },
  "pages": [
    {"page": 1, "template": "blue-white", "objects": [{"name": "title-main", "text": "第一页标题"}]},
    {"page": 2, "template": "blue-white", "objects": [{"name": "title-main", "text": "第二页标题"}]}
  ]
}
```

实际任务对象仍保存 `sourceExtractionId`，或已有的 `measurementEvidence` / 素材来源。公共模板对象可以引用一次真实模板依据；每页独有内容保留逐页来源。示例代码省略来源字段，不是可直接充当 QA 证据的观测记录。

合并规则：

- 先展开所选模板，再按对象 `name` 应用当页补丁。已有同名对象局部覆盖，新对象追加；同一页输入重复名称报错，跨页可以同名。
- 样式通过 `styleRef` 共享，对象的 `style` 覆盖同名属性。普通对象字段递归覆盖，数组整体替换；不会按位置混合段落、图片或数据行。
- `omitObjects: ["name"]` 明确移除该页不需要的模板对象。不能同时删除和覆盖同一对象。
- 改 `text` 时未同时给 `textRuns`，清除继承的旧 runs，防止带入上一页文案。需要保留多色强调时传入相符的新 runs。
- 单页直接提供 `text` 时，同时清除模板继承的 `textFrom`，避免旧计算覆盖用户定稿；仅当该补丁显式给出 `textFrom` 时继续按要求联动。
- 同字号不合并文本框；连续段落与独立条目继续按编辑语义区分。共享模板不会把五页正文变成一个对象。
- 一份 PPTX 共用一个画布尺寸；非 16:9 按实际比例设定，混合比例需分开交付或先明确目标尺寸，不自动拉伸。

## 已支持的构建字段

通用字段为 `name/type/x/y/w/h/z`，可附 `role/editable/sourceExtractionId/measurementEvidence`。`editable` 是需求记录，不能替代最终包内检查。

| type | 主要字段 |
| --- | --- |
| text | `text`、`textRuns[{text,style}]`、`styleRef`、`style.fontFamily/fontSizePt/bold/fontWeight/italic/color/align/verticalAlign/lineSpacingPercent/insets` |
| shape | `shape`（原生几何）、`style.fill/stroke/strokeWidthPx`、`borderRadius` |
| path | `points`（相对对象 bbox 左上角的 px 点列）、线条样式；当前为折线路径 |
| image | `source`（相对输入 JSON 的本地路径或绝对路径）、`fit`、`geometry`、`crop`、`borderRadius` |
| table | `values` 二维矩阵、`columnWidths/rowHeights`（px）、`style/headerStyle`；逐单元格边框 |
| chart | `chartType/categories/series`、`barOptions/xAxis/yAxis/dataLabels/hasLegend`；原生图表 |

图片 `geometry` 可用 `rect/roundRect/ellipse`；正方形框配 `ellipse` 为圆形，非正方形框为椭圆。按内容判断边界，保住主体和必要内容。`crop` 是源图四边裁掉的比例，这是运行时的图片内部裁切参数，不替代页面的 px 坐标。自定义复杂遮罩仍走现有素材策略。

`datasets` 可在整份文件共享，也可逐页按数据集名覆盖。表格用 `dataRef + columns[{field,label}]`；图表用 `dataRef + categoryField + series[{name,valueField,...}]`；文字用 `textFrom:{dataset,aggregate:"sum",field}`。缺字段或非数字值报错，不补零。用户定稿没有明确要求联动时，不用计算结果覆盖其文字。

## 接入 Presentations

1. 按当前 Presentations 规则准备 runtime、标记操作，并按 execution-runner 固定路由。
2. 将 `assets/runtime/` 的三个 `.mjs` 文件复制到任务的 build 脚本目录，连接当前 `node_modules`。无须改系统依赖。
3. 准备 `build-config.json`，只填写当前任务路径与实际 requirements：

```json
{
  "workspaceDir": "当前工作区绝对路径",
  "presentationSkillDir": "实际安装的 Presentations skill 绝对路径",
  "pythonExecutable": "依赖工具返回的 Python 绝对路径",
  "buildDir": "工作区内本版新建且为空的产物目录",
  "finalPath": "工作区 outputs 下未占用的 PPTX 绝对路径",
  "requirements": {}
}
```

通过现有 runner 执行：`node build-from-layout.mjs layout-spec.json build-config.json`。完整命令参数见 [execution-runner.md](execution-runner.md)。输出经过当前 finalizer，再从最终 PPTX 导入渲染。

新建原生图表且明确要从完整字面数据创建内嵌工作簿快照时，可在 requirements 写 `materializeLiteralChartWorkbooks:true`。不自动用它修复或替代已有工作簿、公式与来源。

构建目录自动产生 `resolved-layout.json`、`layout-pages/page-N.json`、`object-map.json`、`metrics.json` 和渲染 receipt。QA 的 `layoutSpecFiles` 引用派生的逐页文件；观测文件继续引用真实抽取，不从最终布局伪造。`object-map` 保留页面、名称、runtimeId、坐标和素材哈希；图片选择窗格名称能否导出取决于当前 runtime，不能仅凭传了 `alt` 就声称命名成功。

旧 2.0 的单页 `objects[]` 结构可以读取，实际填写的字段仍需满足对应对象契约。超出当前字段范围的连接关系、动画、复杂路径和原稿增量修改，继续使用当前运行时能力：任务脚本可导入 `resolveLayout`（显式扩展 allowedTypes）与 `createFromLayout`（handlers），共享同一份数据，只扩展必要对象。不能为迁就构建器而静默栅格化或丢弃关键样式。

## 验收与速度

统一模板任务按“共同模板 + 单页内容要求”比较，归一化的已授权差异不算还原失败。模板校准一次，修改公共模板后检查所有受影响页；只改某页时检查该页及依赖变化。最终仍浏览所有交付页的真实渲染，不重复为相同模板参数做多轮识别和校对。

轻微差异按用户接受范围记录，不为追求 AI 参考图像素一致追加修复循环；缺字、溢出、主体缺失和编辑能力不达约定仍需处理。沿用现有有限返修预算，不新增“模板必须零像素误差”的门禁。

模板省下的是重复分析、填写和编写代码的机会；程序执行时间不等于节省时间。实测提速必须比较同条件的完整任务耗时，不能用渲染或对象构造的几毫秒推算总体加速。
