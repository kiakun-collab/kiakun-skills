# P2 · 健壮性与契约一致性

## P2-1 统一两套页码提取(契约 bug)☑

> 完成(2026-07-05):抽 `_image_common.extract_page_number(path, explicit=None)`,采 make_comparison 的 **label 优先**策略(explicit 映射 → `page/slide/p` 标签 → 唯一裸数字 → None)。`calibrate.render_map` 改用它(删除旧 `page_number` 取「最后一个数字」的分歧实现),make_comparison 删本地版改 import,两处 `import re` 随之移除。新增 `tests/test_page_number_contract.py`(P4-2):断言共享 helper label 优先、且两脚本对同组文件名映射逐一相等(并断言二者引用同一函数对象)。44 测试全绿。

- 定位: `calibrate_reference_render.py:32-52 page_number`(取 stem 最后一个数字)vs `make_reference_render_comparison.py:54-83 extract_page_number`(优先 `page|slide|p` 标签,否则要求唯一数字)。
- 问题: 同一文件名两脚本可能配出不同页码——同一管线内的真实正确性 bug。
- 改动: 抽到 `_image_common.extract_page_number`,两处共用同一策略(建议采用 make_comparison 的标签优先策略)。
- 验收: 新增回归(P4-2)断言两脚本对同组文件名映射一致;calibrate/make_comparison 现有测试全绿。

## P2-2 CJK 叠加字体 ☑

> 完成(2026-07-05,采方案 a / 决策 D2):`_image_common.load_overlay_font(size=14)` 按平台探测系统 CJK 字体(Windows `msyh.ttc`/`simhei`/`simsun` → macOS PingFang/STHeiti → Linux Noto/WQY),`ImageFont.truetype` 命中即用,全部失败回退 `load_default()`,**不往仓库塞字体**。extract/calibrate/make_comparison 的 `ImageFont.load_default()` 全部改为 `load_overlay_font()`(并移除各自已冗余的 `ImageFont` PIL 导入)。新增 `tests/test_overlay_font.py`(P4-3):CJK 文本渲染不抛异常、返回可用字体、Windows 上实测解析到 `FreeTypeFont`(msyh.ttc)而非 bitmap 默认字体。叠加图为 PNG 不进 JSON 契约,49 测试全绿。

- 定位: `ImageFont.load_default()` at `extract:606` / `calibrate:266` / `make_comparison:142`。
- 问题: 无法渲染中文 shape name,标注图标签显示为方框——中文工作流硬伤。
- 改动(**默认走方案 a,见 00-overview 决策 D2**):
  - (a) 新增 `load_overlay_font()` helper:按平台探测系统 CJK 字体(Windows: `msyh.ttc`/`simhei.ttf` → Linux/Mac: Noto/PingFang),找到用 `truetype`,全部失败回退 `load_default()`。不往仓库塞字体文件。
  - (b) 兜底选项(需用户批准):打包开源 CJK 子集字体到 `assets/fonts/`。
- 验收: 新增回归(P4-3):含中文 shapeName 的注释渲染不抛异常;Windows 上人工确认标签可读。

## P2-3 收窄过宽 except ☑

> 完成(2026-07-05):extract 定义 `IMAGE_FAILURE_ERRORS = (OSError, ValueError, UnidentifiedImageError)`,串行与并行两处 per-image 捕获均改为它——编程类异常(如 KeyError)不再被静默降级为「页面失败」而是上抛。score 顶层 try 只包住 read+parse(`OSError`/`JSONDecodeError` → 退出 2,并显式校验 root 为 object),item 循环内新增 per-item `except (KeyError, TypeError, AttributeError)` → 记入 `failures` 不中止。新增 P4-4 回归:`test_all_bad_images_exit_with_code_2`(extract 全坏图退出 2)、`test_single_bad_item_is_recorded_without_aborting`(score 单坏 item 记 failures、好 item 仍评分、退出 1)。46 测试全绿。

- 定位: `extract:851 except Exception`;`score_typography_candidates.py:200` 顶层 `except (OSError, json.JSONDecodeError, KeyError, TypeError)`。
- 问题: extract 会把重构引入的编程错误(如 KeyError)静默降级成"页面失败";score_typography 单个坏 item 中止整文件。
- 改动:
  - extract: per-image 仅捕获 `(OSError, ValueError, PIL.UnidentifiedImageError)`;编程类异常上抛。
  - score_typography: 把 per-item 计算 try 下沉到 items 循环内(`:162` 附近),单 item 失败记入 failures 不中止;顶层仅保留 IO/JSON 解析捕获。
- 验收: P4-4 两个回归(全坏图退出 2;单坏 item 不中止)。

## P2-4 契约文档漂移修正 ☑

> 完成(2026-07-05)`references/script-output-contracts.md`:(a) extract 补记退出码 0(≥1 页成功)/2(全失败)并同步新增的 `--jobs` 参数;(b) calibrate 退出码 0(PASS)/1(FAIL·INCONCLUSIVE)/2(输入错误)区分;(c) 删除不存在的 `overflow` 字段,改为实际的 `clippingDetected`;(d) 基线代理字段名写实为 `baselineProxyPx`,并补 `lineCount`/`lineGapPx`/`failures` 与 score 退出码。`test_mode_selection_contract.py` 不回归,46 全绿。

- 定位: `references/script-output-contracts.md`。
- 修正:
  - (a) extract 全页失败退出码 2(`extract:879`)补记。
  - (b) calibrate 退出码 0/1(`:361`)区分说明。
  - (c) score_typography 契约写的 `overflow` 字段实际不存在,只有 `clippingDetected`(`score:99`)→ 改文档或补字段(二选一,建议改文档)。
  - (d) `baselineProxy` → 实际字段 `baselineProxyPx`(`score:105`)。
- 验收: 文档与脚本实际输出一致;`test_mode_selection_contract.py` 不回归。

## P2-5 make_comparison 缺页容错 ☑

> 完成(2026-07-05):新增 `--allow-missing`。缺失/多余页不再 `raise SystemExit`,页集取 `references ∪ renders`,缺失一侧渲染 `#DDDDDD` 灰格占位并在标注写 "reference/render missing";pairing entry 追加 `status`(matched/missing)。**默认行为逐字节不变**:非 `--allow-missing` 时仍走原硬失败,pairing entry 不含 `status` 字段。新增 `test_allow_missing_renders_placeholder_and_tags_status`。

- 定位: `make_comparison:120-132 raise SystemExit`,任一页错配即整体中止,无部分产出。
- 改动: 增 `--allow-missing`:缺失 render 页降级为占位灰格,pairing JSON 标 `status="missing"`;默认行为(硬失败)保持不变。
- 验收: 默认路径现有测试全绿;新增 `--allow-missing` 用例。

## P2-6 calibrate 容差与页数校验可见化 ☑

> 完成(2026-07-05):新增 `--verbose`。开启时向 **stderr** 打印每页 `tolerancePx` 及其推导(`explicit --tolerance-px=…` 或 `max(6.0, max(w,h)*0.005)`),并在 render 页数 < measurement 页数时打印汇总 warning。**stdout 契约不变**(仍仅 `print(output_path)`)。新增 `test_verbose_adds_stderr_without_changing_stdout`(断言 plain/verbose 的 stdout 相同、仅 verbose 的 stderr 含 `tolerancePx`)。51 测试全绿。

- 定位: `calibrate:328` 静默容差 `max(6.0, max(w,h)*0.005)`;renders 与 pages 数不符仅进 errors。
- 改动: `--verbose` 时 stderr 打印 tolerance derivation;renders 数 < pages 数时打印 warning 汇总(stdout 契约不变)。
- 验收: 无输出契约变化;`--verbose` 手测。
