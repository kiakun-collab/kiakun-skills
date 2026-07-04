# M4 · PowerPoint COM 渲染 + QA 闭环 ✅

> 完成(2026-07-05):`scripts/render_pptx_com.py`(COM 规避清单全实现:Slide.Export 输出像素、WithWindow=False 不碰 Visible、DispatchEx+CoInitialize、context manager 收尾+psutil PID 兜底、watchdog;实测导出 2560×1440 且无僵尸进程)+ `scripts/qa_gate.py`(全页 SSIM + 逐元素 SSIM/MAD 兜底 + 文字折行一致性;复用同级 make_comparison 对照大图,D4 路径解析+env 覆盖;defect 分类 + `apply_repairs` 修复策略——文字只加宽绝不烘焙、视觉 defect 最小降级烘焙)。`tests/test_qa.py` 7 测试(自比 PASS、颜色差 defect、折行不一致、SSIM 自比=1、defect 分类、toolkit 缺失报错、repair)+ `tests/test_render_com.py`(skipif:2560×1440+无僵尸)。返修**循环**在 M5 run_pipeline。

产出:`scripts/render_pptx_com.py` + `scripts/qa_gate.py`(编排复用 ppt-rebuild QA 工具)+ 返修逻辑。

## COM 渲染器(render_pptx_com.py)

规避清单(2026-07-05 调研结论,全部照做):

1. **导出**:`Slide.Export(path, "PNG", ScaleWidth, ScaleHeight)`——第 3/4 参就是输出像素;2x = `2 × 960/72 × 96 = 2560`(即 2560×1440,与参考图同尺寸)。**不用** SaveAs(那个才受注册表 DPI 限制)
2. **隐藏运行**:`Presentations.Open(path, ReadOnly=True, Untitled=False, WithWindow=False)`;**绝不碰 `Application.Visible=False`**(会抛 Invalid request)
3. **实例**:`win32com.client.DispatchEx` 起新实例;非主线程先 `pythoncom.CoInitialize()`,退出 `CoUninitialize()`;gencache 出错时删 gen_py 缓存目录重试
4. **僵尸进程**:context manager——关所有 Presentation → `app.Quit()` → `del` 引用 → `gc.collect()` → 校验进程退出,超时按启动时记录的 PID kill(psutil);启动前发现残留实例先清
5. **弹窗**:`app.DisplayAlerts = 1`(ppAlertsNone);Office 未激活的许可弹窗无法抑制 → 文档写明环境前置;Open/Export 外层套 watchdog 超时(默认 120s/页)
6. 交互式会话前置(非 service);CLI:`--pptx --out-dir [--scale 2] [--pages 1,3-5]`

## QA 编排(qa_gate.py)

复用 ppt-rebuild 工具(路径按 00-overview D4 解析):

```
参考图(M1 reference@2x)+ COM 渲染图(@2x)
  → calibrate_reference_render.py   坐标偏移/锚点校准(PASS/INCONCLUSIVE/FAIL)
  → make_reference_render_comparison.py  逐页对照大图
  → 像素门禁:全页 SSIM ≥ 阈值(建议 0.93 起步,校准后定)
  → 逐元素门禁:按 layout-spec bbox 切块对比,超阈值元素列入 defects[]
  → 文字门禁:折行一致性(渲染图上该段行数 vs textLayoutBudget)
```

产出 `qa-report.json`:整体判定、defects[](元素 id/类型/偏差量)、校准状态、对照图路径。

## 自动返修(≤3 轮,第 0 轮为首建)

按 defect 类型分派修复策略:
- 位置偏移(校准给出全局 dx/dy)→ 整体平移重建
- 单元素几何/样式偏差 → 调整该 shape 参数重建
- 文字折行不一致 → 框宽 +2%,仍失败 → 字号 -0.5pt(限一次),再失败 → 该文本框保持原样 + 报告(**不烘焙文字**,可编辑度优先)
- 非文字元素视觉差异大 → **最小降级**:该元素单独烘焙(Playwright 按 DOM 路径 `element_handle.screenshot()` @2x)替换,记 bakedReason="qa-downgrade"
- 3 轮后仍 FAIL → 交付但报告置 `overallStatus: "PARTIAL"`,defects 全量列出

## 验收

- COM 渲染器:本地测试(`skipif` 无 PowerPoint)——3 页样例 pptx 导出 3 张 2560×1440 PNG;进程无残留(psutil 断言);watchdog 超时路径可测(mock 卡死)
- QA 编排:用**同一张图自比**必 PASS;人工偏移 5px 的渲染图必被 calibrate 捕获
- 返修:注入单元素颜色偏差 fixture → 第 1 轮修复;注入 backdrop 类不可修 → 降级烘焙且 bakedReason 正确
- 端到端(本地):M1-M4 全链对 3 个 golden 样页跑通,双门禁 PASS
