# M5 · Skill 封装与交付 ✅

> 完成(2026-07-05):`scripts/run_pipeline.py`(进程内编排 extract→transform→bake→build→render→qa→**返修循环** ≤3 轮,文字加宽/视觉降级烘焙,Playwright 按 selectorPath 逐元素 @2x 补截;`--steps` 子集、`--stop-on-fail`;PARTIAL 语义)+ `SKILL.md`(中文,触发条件/Start Here/坐标系/烘焙策略/QA/降级/环境前置)+ `references/pipeline-contracts.md`(四契约+CLI+退出码)+ `pyproject.toml`(Pillow/python-pptx/playwright/numpy/scipy/psutil + pywin32 win32-only;`pip install -e` 通过)。`tests/test_contracts.py`(schema↔契约文档一致)+ `tests/test_e2e.py`(离线 build + svg 烘焙 + 完整双门禁 skipif)。**全套 41 测试全绿**(离线组 37 + COM 组 4,离线组无 PowerPoint 也全绿);完整 COM 链路实测跑通并产出 qa-report。

产出:SKILL.md、契约文档、流水线驱动、pyproject、端到端测试。

## 清单

1. **`scripts/run_pipeline.py`**:extract → transform → build → render → qa → 返修循环的一键驱动;`--steps` 子集;`--stop-on-fail`;聚合 `pipeline-report.json`(沿用 ppt-rebuild P3-1 的模式:纯 subprocess 编排,不重复实现逻辑)
2. **`SKILL.md`**(中文,风格对齐 ppt-rebuild):
   - 触发条件:用户给 HTML(AI 生成 slide、网页片段)要可编辑 PPT
   - Start Here:一条 run_pipeline 命令 + 常用参数
   - 输入约定:1280×720 固定比例;多页=多文件或整页高度切;**仅 16:9**(沿用 ppt-rebuild D1 决策口径,非 16:9 声明降级)
   - 可编辑边界说明、烘焙策略、QA 等级、失败降级(PARTIAL 语义)
   - 环境前置:PowerPoint 已激活、交互式会话、playwright chromium
3. **`references/pipeline-contracts.md`**:extraction.json / layout-spec.json / qa-report.json / pipeline-report.json 四个契约 + 各脚本 CLI 与退出码(0 成功 / 1 门禁 FAIL / 2 输入错误)
4. **`pyproject.toml`**:`Pillow`,`python-pptx`,`playwright`,`pywin32`;`[fast]`=numpy/opencv(QA 工具用);`[dev]`=pytest
5. **测试组织**:`tests/`——离线组(fixtures、M2/M3 单测、契约测试)+ 本地组(COM/E2E,skipif);`tests/fixtures/` 放 3 个 golden HTML 样页
6. **交付报告字段**(qa-report 汇总进最终输出):文件路径、页数、原生对象数/烘焙数(+逐个 bakedReason)、fontMap、defects、QA 轮数、PARTIAL 项

## 验收

- 新会话冷启动测试:仅凭 SKILL.md 指引,agent 能对一个新 HTML 完成全流程(不读 implementation-plan)
- 契约测试:contracts 文档与各脚本实际输出一致(ppt-rebuild `test_mode_selection_contract.py` 风格)
- `pip install -e .[fast,dev]` 可装;离线测试组在无 PowerPoint 机器上全绿
