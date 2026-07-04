# M3 · PPTX 构建器(layout-spec.json → .pptx) ✅

> 完成(2026-07-05):`scripts/build_pptx.py` + `scripts/_oxml_helpers.py`。逐角色:shape→autoshape(rect/roundRect,adj 圆角)、渐变/outer shadow/透明度走 OXML、text→textbox(`<a:noAutofit/>`、margins=padding、runs 粗斜色字号、CJK 补 latin+ea)、image→picture(本地文件嵌入,否则透明占位+登记 pendingBake)、旋转 rot=度、group 用**恒等变换 grpSp**(off==chOff/ext==chExt,子形状保绝对坐标)、table v1 由单元格 text 呈现(原生表格留 v2)。`tests/test_build.py` 7 测试全绿(solid+round+shadow+rot、渐变 stops+ang、noAutofit+run 属性、CJK ea、group 恒等变换 2 子、baked 占位+pendingBake、形状计数)。

产出:`scripts/build_pptx.py`(python-pptx;个别 python-pptx 不支持的属性直接操作 lxml XML)。

## 坐标与画布

- 幻灯片:12192000×6858000 EMU(标准 16:9);换算 `px × 0.75 × 12700 = EMU`(1280×720 px 恰好满幅,无缩放因子)
- 全部绝对定位,不用占位符/版式;母版留空白版式

## 逐角色构建规则

| 角色 | PPTX 对象 | 要点 |
|---|---|---|
| `shape` | autoshape(rect/roundRect) | 四角圆角用 `adj` 或自定义 geometry;渐变 fill 用 XML(python-pptx 渐变支持弱);outer shadow 用 `<a:effectLst>` XML |
| `text` | textbox | **autofit 关闭**(`<a:noAutofit/>`);margins 按实测 padding;runs 按 M2 的 runs(粗/斜/色内联);`wrap=square`;字体用 fontMap 目标字体,CJK 时 eastAsian+latin 分别指定 |
| `image` | picture | 源图原始字节直接嵌入(不重编码);object-fit:cover → 裁剪(srcRect) |
| `table` | graphicframe table | 列宽/行高按实测;单元格边框/底色/对齐 |
| `baked` | picture(占位) | M3 阶段先放**占位透明 PNG**并登记 `pendingBake` 清单,M4/driver 调 Playwright 按 DOM 路径补截(避免 M3 依赖浏览器) |
| `group` | group shape | 按 groupId;组内坐标换算注意 chOff/chExt(参考 ppt-rebuild `group_transform` 的逆运算) |
| 旋转 | 任意 shape | 用 M1 未变换盒 + `rot`(EMU 角度 = 度 × 60000);注意 PPT 旋转锚点是中心,CSS transform-origin 需换算 |

## 关键风险与对策

1. **文字折行漂移**(最大还原度风险):autofit 关 + 宽度按行盒并集 + `textLayoutBudget` 中每行宽度余量 ≥ 4%;若某段落预算余量不足(浏览器行宽逼近框宽),构建时框宽 +2px 冗余。QA 轮(M4)用 overlap 审计兜底
2. python-pptx 渐变/阴影 API 缺口:统一封装 `_oxml_helpers.py`,写原始 `<a:gradFill>`/`<a:effectLst>`;每个 helper 带最小 XML 单测
3. z-order:python-pptx 按插入序即 spTree 序,构建按 `zOrder` 排序后插入
4. 字体不存在时(fontMap 置信度低):照写目标字体名 + 报告 warning,不擅自替换第二次

## 验收

- 单测(无浏览器/COM):golden layout-spec → 生成 pptx → 用 zipfile+lxml 断言:
  - 形状数/文本框数/组结构与 spec 一致;autofit 已关;字体名/字号/颜色正确
  - 渐变 stops、shadow 参数、圆角 adj 写入正确
  - 旋转形状 rot 值正确;组内子形状坐标换算正确(可复用 ppt-rebuild `_pptx_common.group_transform` 做逆向验证)
  - baked 占位登记 `pendingBake` 完整
- 产物用 ppt-rebuild 的 `audit_pptx_structure.py` 跑一遍无 imageOnlyRisk(烘焙占比受控)
