# PPT-Rebuild-Workflow 优化计划 · 总览与执行规约

> 规划 agent 维护;实际开发由执行 agent 完成。每份 PX 文档可独立派单,但必须先读本文件。
> 最后更新:2026-07-05

## 规划方验收(2026-07-05)

**结论:通过。** 独立复核(非仅采信执行记录):64 测试实跑全绿;`_pptx_common`/`_image_common`/`_io_common`/`run_pipeline.py`/`pyproject.toml` 均在位;抽查 P2-1(calibrate 与 make_comparison 均 import 共享 `extract_page_number`,旧分歧实现已删)、P5-1(qa-gates.md 已建)、P5-6(SKILL.md:18 已改为 16:9 声明降级)、P3-2(--doctor 实测输出正确引擎)、P3-1(driver 为纯 subprocess 编排)属实。P0-1 的偏离(实测证伪 ≥10× 前提后回滚 FFT 方案、改为 2.5× 安全优化)有基准数据与等价性验证支撑,处置正确。遗留 backlog:P5-1 物理去重、P5-2、P3-4、P0-4/0-5,均低优先且已附暂缓理由;其中 P5-1 物理去重是唯一未兑现的规划收益(Mode B 文档量未净减),建议下次以契约测试为护栏做 focused session。完成定义中「≥10× 提速」与「文档量净减 200-300 行」两条按验收结论**作废/降级**,以实际结项口径为准。

## 执行进度(2026-07-05)

- **P1 全部完成** ✅:P1-1 `_pptx_common`、P1-2 `_image_common`、P1-3 `_io_common`、P1-4 `pyproject.toml`。
- **P0**:P0-1 ✅(用户拍板接受:调研+2.5× fallback 优化+补两条路径覆盖;≥10× 前提不成立已存证)、P0-2 ✅(numpy 路径就位,纯 Python 保留)、P0-3 ✅(并行化,逐字节一致)、P0-4 暂缓(可选低优先)、P0-5 暂缓(仅惠及降级路径)。
- **P2 全部完成** ✅:P2-1〜P2-6。
- **P3**:P3-1 ✅(run_pipeline 驱动器)、P3-2 ✅(--doctor)、P3-3 ✅(--verbose)、P3-5 ✅(安静模式);P3-4 暂缓(缓存,风险>收益)。
- **P4 全部完成** ✅:P4-1〜P4-4 随 P0/P2 落地、P4-5 group_transform 直接单测。
- **P5**:P5-3/4/5/6/7 ✅;P5-1 ◐(qa-gates.md 单一源已建并引用,物理去重受契约测试钉字约束暂缓);P5-2 暂缓(保守不合并)。
- **测试**:基线 37 → 当前 **64 全绿**(新增 27 条回归/覆盖/单测)。
- **暂缓项(均附理由)**:P0-4、P0-5、P3-4、P5-1 物理去重、P5-2 —— 皆为低收益或受契约测试约束的高风险精修,建议留独立 focused session。

## 背景

7 个脚本 + 17 份 reference 文档 + 模板 + 测试构成 PPT 还原工作流。本计划分 6 个优先级(P0-P5):
P0 性能与正确性、P1 去重与依赖、P2 健壮性与契约、P3 功能补齐、P4 测试补强、P5 文档体系。

## 全局规约(所有执行 agent 必读)

1. **禁止改变对外 JSON 字段字节级输出**,除非该文档明确要求。现有测试用 subprocess 断言输出,任何漂移会被捕获。
2. 改动前先跑 `python -m pytest tests/ -q`(或 `python -m unittest discover tests`)建立绿色基线(当前 37 全绿)。
3. 保持 `encoding="utf-8"` + `ensure_ascii=False` + `print(output_path)` 的既有 stdout 契约。
4. 退出码语义不得随意更改(见各脚本 `main()`)。
5. 不得引入未在 `pyproject.toml`(P1-4 建立)声明的新依赖。
6. Python 目标版本 >= 3.9。
7. 文档改动必须保持 `tests/test_mode_selection_contract.py` 通过。
8. 完成一项就在对应 PX 文档中打勾并附一行变更摘要。

## 已确认的决策(2026-07-04 用户拍板)

| # | 决策点 | 结论 |
|---|---|---|
| D1 | 非 16:9 支持 | **仅支持 16:9**;其他比例明确声明降级路径(见 P5-6 方案 b) |
| D2 | CJK 叠加字体方案 | **系统字体探测优先**,不打包字体文件;全部探测失败才回退 `load_default()` |
| D3 | 执行范围 | **P0-P5 全部执行** |

## 推荐执行顺序(有依赖关系)

1. **P1-4**(依赖清单)→ **P1-1/1-2/1-3**(共享模块)← 铺底,先做
2. **P0-1 / P0-2**(calibrate 向量化,依赖 P1-2 的 edge_binary)
3. **P0-3 / P0-5**(extract 并行 + 去重扫描)
4. **P2 全组**(健壮性/契约,含 P4 对应回归)
5. **P5 文档体系**(独立于代码线,可与 2-4 并行)
6. **P3 功能**(驱动器/doctor/进度/缓存)
7. 最后 **P0-4** 与剩余 **P4**

## 关键风险控制

- **P0-1 会动匹配阈值的数值语义**:改动前用 `test_calibrate_reference_render.py::test_measures_known_translation` 固定基线,改后比对 dx/dy 与 confidence,防精度回归。
- 共享模块抽取必须保持输出字节级一致(subprocess 测试兜底)。

## 脚本清单与行数(定位参照)

- scripts/extract_reference_measurements.py (883)
- scripts/audit_pptx_text_frames.py (572)
- scripts/audit_pptx_structure.py (508)
- scripts/calibrate_reference_render.py (365)
- scripts/validate_rebuild_evidence.py (249)
- scripts/score_typography_candidates.py (210)
- scripts/make_reference_render_comparison.py (206)

## 完成定义(整体)

- 全部单测通过 + 新增回归通过。
- `pyproject.toml` 存在且 `pip install -e .[fast,dev]` 可装。
- calibrate 无-cv2 路径基准提速 >= 10×(见 P0 基准脚本)。
- Mode B 默认加载文档量下降 200-300 行(P5)。
