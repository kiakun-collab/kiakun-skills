# M1 · Playwright 提取器 ✅

> 完成(2026-07-05):`scripts/extractor.js`(注入式 DOM 遍历:bbox/transform 分解/背景渐变/边框圆角/阴影/逐行文字 Range 矩形/runs/图片/栅格化标记/paintIndex/DOM 路径 id)+ `scripts/extract_html.py`(Playwright chromium,viewport 1280×720,DPR=2,`document.fonts.ready` 等待,fixed 分页按 720 clip,截图 clip→2560×1440)。5 个 golden fixture(text/cards/svg-table/rotate)。`tests/test_extract.py` 8 测试全绿:标题几何、2 行折行 y 单调、卡片渐变/圆角/边框/阴影、旋转分解未变换盒+30°、svg/table/td 检出、DPR=2 截图、paintIndex 单调、fonts.ready 后几何确定性。

产出:`scripts/extract_html.py` + 注入脚本 `scripts/extractor.js`(单文件,evaluate 注入)。

## 输入/输出

- 输入:`--html <file|dir>`(dir 时按 `natural_key` 排序,一文件一页)、`--paginate fixed`(单文件高度 N×720 → 逐屏切 N 页,默认)、`--out-dir`
- 每页输出:
  - `reference/page-<n>.png` — DPR=2 截图(2560×1440)
  - `extraction/page-<n>.json` — 元素树(见 schema)
- stdout:输出目录路径;`--json` 时打印页清单摘要

## 提取内容(注入 JS 遍历 DOM)

每个元素记录:
- `bbox`:`getBoundingClientRect()`(CSS px)。**注意:返回的是 post-transform AABB**——旋转元素要另行处理(下述)
- `transform`:`getComputedStyle().transform` 矩阵。非 identity 时分解出 rotate/scale/translate,同时用 `offsetWidth/Height` + 祖先矩阵累积算出**未变换盒**,两者都写入 JSON(M3 用未变换盒 + `rot` 生成 PPTX 旋转形状)
- 样式:背景色/渐变(原始 CSS 串 + 解析后的 stops)、边框(宽/色/style/radius 四角)、box-shadow、opacity、overflow、z-index、`mix-blend-mode`
- 文字:逐 text node 用 `Range.getClientRects()` 取**逐行矩形**;记录 font-family(完整 fallback 链)、size、weight、style、line-height、letter-spacing、color、text-align、white-space;行矩形按 y 聚类得行盒
- 图片:`<img>` 的 naturalSize + currentSrc;背景图 url;`<svg>` outerHTML;`<canvas>` toDataURL(尝试,污染时标记)
- 绘制顺序:按 DOM 顺序 + stacking context 规则计算实际 paint order,写 `paintIndex`
- 可见性过滤:`display:none`/`visibility:hidden`/零尺寸/视口外(±容差)直接跳过
- **栅格化标记**(供 M2 评分,这里只记录事实):`backdrop-filter`、非 none `filter`、`clip-path`、`mask`、`mix-blend-mode≠normal`、canvas、video、含 filter/mask/多 path 的 SVG

## 关键实现约束(来自 2026-07-05 调研,勿踩坑)

1. **字体加载**:几何提取前必须 `await page.evaluate("document.fonts.ready")`——截图自带等待但 evaluate 不带,不等会导致字体交换后行盒漂移
2. **DPR**:context `device_scale_factor=2`;所有 DOM API 仍返回 CSS px,唯一坐标空间,不要混
3. 视口固定 `1280×720`;fixed 分页用整页高度截图后按 720 切,或逐段 `scrollTo` + clip 截图(选实现简单且无 sticky 元素干扰的方案,写明选择)
4. 元素级烘焙素材此阶段**不截**(M4 返修时按需截,避免浪费);但 `element_handle.screenshot()` 的定位信息(selector 路径)要存
5. 每元素记录稳定 `id`(DOM 路径),贯穿全管线用于 QA 溯源

## 验收

- 3 个 golden HTML fixture(纯文字排版页 / 卡片+渐变+阴影页 / 含 SVG 图标+表格页),提取 JSON 对关键元素的 bbox/字体/颜色断言(chromium 版本 pinned,几何稳定)
- 旋转元素 fixture:断言未变换盒 + rot 角度正确(误差 <0.5°)
- 逐行文字:两行折行段落断言行数=2 且行盒 y 单调
- `document.fonts.ready` 前后几何一致性由 fixture 用 web font 触发验证
- 测试离线可跑(fixture 本地文件,无网络)
