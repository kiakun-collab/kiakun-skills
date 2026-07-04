# html-to-pptx Skill · 实施计划总览

> 规划 agent 维护;实际开发由执行 agent 完成。每份 MX 文档可独立派单,但必须先读本文件。
> 创建:2026-07-05

## 执行进度(2026-07-05)· 全部完成 ✅

M1 提取器 ✅ · M2 变换层 ✅ · M3 构建器 ✅ · M4 COM+QA ✅ · M5 封装 ✅。**41 测试全绿**(离线 37 + COM 4)。完整 COM 链路实测跑通(HTML→PPTX,COM 渲染 2560×1440 无僵尸,双门禁产出 qa-report)。`pip install -e` 通过。已知 v2 留项:原生表格提取(当前 table 由单元格 text 呈现)、`--svg-as-shapes` freeform、返修字号-0.5pt 二级升级。

## 目标

把 AI 生成的固定比例 HTML 页面转换为 PPTX,三个硬指标:

1. **超高还原度**:浏览器渲染结果与最终 PPTX 渲染结果像素级接近(QA 双门禁验收)
2. **超高可编辑度**:文字=原生文本框、形状=原生 autoshape、表格=原生表格、图片=独立对象;仅不可表达元素才烘焙
3. **干净整洁**:无冗余 wrapper 形状、同 bounds 嵌套合并、分组反映语义结构、z-order 正确

## 已确认的决策(2026-07-05 用户拍板)

| # | 决策点 | 结论 |
|---|---|---|
| D1 | QA 渲染后端 | **PowerPoint COM**(本机已装 Office16);**不用 LibreOffice** |
| D2 | 分页 | **固定切**:输入为 AI 生成的固定比例 HTML,按 1280×720 CSS px 逐屏切页;也支持一文件一页 |
| D3 | Skill 形态 | **独立新 skill** `html-to-pptx` |
| D4 | QA 脚本复用方式 | 默认**路径复用**同级 `../ppt-rebuild-workflow/scripts`(calibrate/comparison 已测试稳定,fork 会漂移);环境变量 `HTML2PPTX_QA_TOOLKIT` 可覆盖;找不到时报错并提示。⏳ 若用户要求完全隔离,改为 vendor-copy(需用户确认) |

## 核心架构(方案 C:浏览器渲染 + DOM 几何提取)

```
输入 HTML(单文件多页 / 多文件)
  │
  ▼ M1 提取:Playwright(chromium, 1280×720 视口, DPR=2 截图)
  │   每页产出:reference@2x.png + extraction.json(元素几何/样式/文字逐行/绘制顺序)
  ▼ M2 变换:角色分类 → 扁平化 → 可表达性评分 → layout-spec.json
  ▼ M3 构建:python-pptx → 输出 .pptx(原生对象 + 元素级烘焙 PNG)
  ▼ M4 QA:PowerPoint COM 导出 PNG@2x → 对比参考图(复用 ppt-rebuild 校准/对照/门禁)
  │   ≤3 轮自动返修;仍不过 → 最小降级(单元素烘焙)+ 报告
  ▼ 交付:.pptx + qa-report.json + 对照图
```

### 坐标系(零损耗映射,全程唯一)

- 1280×720 CSS px = 960×540 pt = 标准 16:9 幻灯片(12192000×6858000 EMU)
- 换算:`px × 0.75 = pt`;`pt × 12700 = EMU`
- DPR=2 只影响截图位图;所有 DOM API 返回 CSS px。与截图像素比较时才 ×2

## 全局规约(所有执行 agent 必读)

1. 技术栈锁定:Python ≥3.9 + Playwright(chromium)+ python-pptx + pywin32;不引入 Node 构建链
2. 每个里程碑完成即建立/更新测试,`python -m pytest tests/ -q` 全绿才算完成
3. COM 相关测试标记 `@pytest.mark.skipif`(无 PowerPoint 环境跳过),其余测试必须离线可跑(golden HTML fixtures)
4. JSON 产物字段一经 M2 定稿即为契约,后续只增不改不删;契约写入 `references/pipeline-contracts.md`
5. stdout 只打印最终产物路径;进度/警告走 stderr;全部 `--json` 可选
6. 输出文件 `encoding="utf-8"`、`ensure_ascii=False`;stdout 加 `reconfigure(errors="backslashreplace")` 防 GBK 控制台崩溃(ppt-rebuild P1-3 同款教训)
7. 完成一项在对应 MX 文档打勾并附一行变更摘要;发现计划不合理**回报规划方修订**,不得自行偏离

## 环境前置(已验证 2026-07-05)

- PowerPoint Office16:`C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE` ✅(**须已激活**,许可证弹窗无法用属性抑制)
- pywin32 ✅;Playwright 1.58 + chromium ✅;python-pptx 1.0.2 ✅
- COM 要求交互式会话(非 service/Session 0)

## 里程碑与派单顺序

| 里程碑 | 内容 | 依赖 |
|---|---|---|
| M1 | Playwright 提取器(几何/样式/文字/截图) | 无 |
| M2 | 变换层(分类/扁平化/评分/layout-spec) | M1 的 JSON 格式 |
| M3 | python-pptx 构建器 | M2 的 layout-spec |
| M4 | COM 渲染 + QA 闭环 + 返修 | M3 产出 + ppt-rebuild QA 工具 |
| M5 | SKILL.md + 契约文档 + 流水线驱动 + 端到端测试 | M1-M4 |

M1 与 M2 的 schema 设计需一次定稿(先写 contracts 再动工);M3 可与 M4 的 COM 渲染器并行开发。

## 竞品结论(为什么自研,2026-07-05 调研)

- **dom-to-pptx**(最接近):同样走 DOM 测量绝对定位,验证了路线可行;但无栅格化兜底、无逐行文字几何、无 QA 闭环、CORS 字体静默降级。可借鉴:「测最终盒子、无视布局语义」原则、`svgAsVector` 可选开关
- **Marp `--pptx`**:整页图不可编辑;`--pptx-editable` 走 LibreOffice,文本框过窄换行错乱,官方自认低还原
- **Aspose.Slides**:语义解析 HTML 标签,无浏览器布局引擎,flex/grid/绝对定位全丢
- **PptxGenJS tableToSlides**:只转 `<table>`

## 完成定义(整体)

- 5 个里程碑全部验收;端到端:3 个风格迥异的 AI 生成 HTML 样页 → PPTX,QA 双门禁 PASS
- 可编辑度:样页中文字/形状/表格 100% 原生对象(烘焙仅限评分判定的不可表达元素,且逐个列入报告)
- 整洁度:形状数 ≤ 视觉可见元素数 × 1.3;无零尺寸/同 bounds 重复形状
- 测试:离线套件全绿 + COM 本地套件全绿
