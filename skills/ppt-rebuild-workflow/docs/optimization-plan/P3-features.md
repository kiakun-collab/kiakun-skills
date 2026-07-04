# P3 · 功能补齐

## P3-1 顶层流水线驱动器 run_pipeline.py ☑

> 完成(2026-07-05):新建 `scripts/run_pipeline.py`,仅用 subprocess 串联各脚本、不重复实现分析。顺序 audit_structure → audit_text_frames → extract →(有 `--renders-dir` 时)calibrate →(有 `--typography-input` 时)score →(有 `--renders-dir` 时)make_comparison →(有 `--qa-report` 时)validate。缺输入的步骤标 `skipped` 不算失败;聚合每步 status/exitCode/output/stderrTail 写 `pipeline-report.json`;支持 `--steps` 子集、`--stop-on-fail`。新增 `tests/test_run_pipeline.py`(端到端跑 make_basic_pptx 造的 deck + 参考图/渲染图,断言可用步骤 ok、无输入步骤 skipped;`--steps` 子集只跑指定步)。56 全绿。

- 问题: 7 脚本需手工串联,无 all-in-one。
- 改动: 新建 `scripts/run_pipeline.py`:输入 deck.pptx + reference-dir + out-dir,依次: audit_structure → audit_text_frames → extract → calibrate → score_typography(可选)→ make_comparison → validate_rebuild_evidence。聚合每步退出码与产物路径,输出 `pipeline-report.json`;任一硬失败可 `--stop-on-fail`;支持 `--steps` 只跑子集(agent 仍可单步控制)。
- 契约: 复用各脚本 main() 或 subprocess 调用;**不重复实现分析逻辑**。
- 验收: 端到端跑通 `tests/common.make_*` 造的 deck,产物齐全。

## P3-2 引擎自检 --doctor ☑

> 完成(2026-07-05):extract 加 `--doctor`(input/output 改为非必需,`--doctor` 时早退):打印 `measurement_engine()` 选择、`PPT_REBUILD_MEASUREMENT_ENGINE`、numpy/scipy/cv2 可用性,python 引擎时给慢路径警告与安装建议。回归 `test_doctor_reports_engine_and_dependencies`。

- 改动: extract(或独立 diagnose 脚本)加 `--doctor`:打印 `measurement_engine()` 选择(`extract:38-48`)+ cv2/numpy/scipy 可用性 + 慢路径警告与建议。
- 目的: 长任务前预知是否走慢路径。
- 验收: 有/无 numpy 环境下输出正确引擎名。

## P3-3 进度输出 --verbose ☑

> 完成(2026-07-05):extract 加 `--verbose`,串行逐页、并行按完成顺序向 **stderr** 打印 `page k/N`;stdout 仍只打最终路径。calibrate 的 `--verbose`(P2-6)已逐页打印 tolerance 推导,一并满足。回归 `test_verbose_prints_progress_to_stderr_only`。

- 定位: extract / calibrate 长任务仅末尾 `print(path)`。
- 改动: `--verbose` 时逐页向 **stderr** 打印 `page k/N (name)`;stdout 仍只打最终路径(保持调用方解析契约)。
- 验收: 无 `--verbose` 时输出零变化。

## P3-4 增量缓存 --no-cache ☐(暂缓,建议留焦点专项)

> 评估(2026-07-05):价值有限——extract 逐页已在 P0-3 并行化,该工作流对同一未变参考图重复整跑的场景罕见;而缓存层带**逐字节一致**硬约束(缓存的 page dict 与注释 PNG 必须与新算完全一致,含缓存失效键 path+mtime+size+params-hash 的正确性),风险明显高于收益。建议留独立专项实现:缓存 per-page result dict 到 `out-dir/.cache/`、命中即复用并跳过重绘(需校验 PNG 仍在),再加「二次运行 JSON 与首次逐字节一致 + 显著提速」回归。当前暂缓。

- 改动:
  - extract: 参考图未变(mtime+size 或内容 hash)则跳过重算注释 PNG。
  - calibrate: 缓存 edge array(基于 render/reference 路径+mtime)。
  - 默认启用,`--no-cache` 关闭。缓存存 `out-dir/.cache/`。
- 验收: 二次运行显著加速且 JSON 输出与首次一致。

## P3-5 audit_structure 安静模式 ☑

> 完成(2026-07-05):加 `--print-json`。有 `--output` 时 stdout 默认只打紧凑摘要(slideCount/各计数/imageOnlyRisk/fullSlideImageRiskPages),`--print-json` 打完整 JSON;无 `--output` 时仍打完整 JSON(零丢失)。契约文档同步。回归 `test_output_prints_compact_summary_unless_print_json`。

- 定位: `structure:496-503` 总是打完整 JSON 到 stdout。
- 改动: 有 `--output` 时默认仅打 totals 摘要(对齐 `text_frames:567` 行为);`--print-json` 显式全量。
- 验收: 无 `--output` 时行为不变;`test_audit_pptx_structure.py` 相应调整/新增。
