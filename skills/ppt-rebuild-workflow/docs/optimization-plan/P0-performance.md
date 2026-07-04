# P0 · 性能与正确性(最高优先级)

前置:建议先完成 P1-2(`_image_common.edge_binary`)。若尚未完成,可在本任务内临时内联,后续再抽取。

## P0-1 重写 calibrate 纯 Python 锚点匹配 ☑(已按用户决策结项:调研 + 安全优化)

> **用户决策(2026-07-05):接受当前方案**——保留 2.5× fallback 优化 + 两条路径覆盖测试,视 numpy 为性能推荐依赖(已在 `[fast]`),不追求 ≥10×。
>
> 调研结论(2026-07-05,附基准,1280×720 坐标系 = extract 默认 target):
> - **前提有误**:所谓「无 cv2 分钟级瓶颈」并不在 `match_anchor_fast` 的 numpy 分支。实测该分支 20 页×10 锚点仅 **0.58s**(每锚点 ~2.9ms),因为逐 offset 的 `count_nonzero` 已是 numpy 向量化。对它再做 FFT/滑窗向量化反而**更慢**:fftconvolve 0.6×、sliding_window_view 0.1×(小 radius=12 下 FFT 每锚点开销压过收益)。已实现并用 300 组随机数据验证**逐值精确等价**(dx/dy 完全一致),但因是性能倒退,**已回滚不采用**。
> - **真正的分钟级瓶颈**是 `match_anchor` 的**纯 set 版**(仅在 **numpy 也缺失**时才走):20 页×10 锚点约 **74s**。但该路径无 numpy,**无法向量化**。
> - **已落地的安全优化**:利用「分母跨 offset 恒定 ⇒ 排序等价于比 intersection 计数」,把 set 版每 offset 重建 shifted set 改为直接 membership 计数,**2.5× 提速且输出逐值一致**(74s→~30s)。
> - **新增覆盖**:`test_no_cv2_numpy_branch_matches_known_translation`(强制 cv2=None)、`test_pure_python_fallback_matches_known_translation`(强制 np=None),此前这两条匹配路径 **零测试覆盖**。
> - **建议**:①numpy 属 `[fast]` 且极常见,建议将其视为性能必需(纯 Pillow 属降级模式);②若仍要 ≥10× 且面向纯 Pillow 机器,唯一路径是要求安装 numpy(等于取消该 case),或接受 2.5× 纯 Python 优化。**是否勾选此项、以及是否要我按建议①调整依赖/文档,请用户定夺。**

- 定位: `calibrate_reference_render.py:104-157`(`match_anchor_fast` 无 cv2 分支 132-147)、`:174-204`(`match_anchor` set 版)。
- 问题: radius=12 → 每锚点 625 次偏移循环;`match_anchor` 每次重建 shifted set 求交。无 cv2 机器主瓶颈(10 anchors × 20-50 页时是分钟级)。
- 改动:
  1. 无 cv2 且有 numpy 时,用滑窗互相关一次算全偏移得分图:对二值 template 与 search 做 `scipy.signal.fftconvolve(search, template[::-1,::-1], mode='valid')`;无 scipy 时用 `np.lib.stride_tricks.sliding_window_view` + 张量点积。取 argmax → best_dx/dy。
  2. 删除 `match_anchor`(纯 set 版)及其调用(`analyze_page:244-252`),统一走数组路径;仅在 numpy 也缺失时才退化到逐点(保留一个最小实现)。
  3. 重新标定阈值:FFT/IoU 得分与 `TM_CCOEFF_NORMED` 不同尺度,需校准 `:149` 和 `:197` 的 `>=0.12`。
- 验收:
  - `test_calibrate_reference_render.py` 全绿。
  - 强制 cv2=None 的 known-translation 用例(见 P4-1)dx/dy 与旧 set 版一致(±1px)。
  - 基准:20 页 × 10 anchor,无 cv2,耗时下降 >= 10×。

## P0-2 向量化像素级循环 ☑(numpy 路径)/ 纯 Python 保留

> 状态(2026-07-05):**有价值的 numpy 向量化均已就位**——`edge_mask` 已在 P1-2 委托给 `_image_common.edge_binary`(numpy 分支 `np.frombuffer>=threshold`);`line_candidates` 垂直/水平 counts 早已用 `array.sum(axis=0)`/`sum(axis=1)`。`edge_points→ndarray` 一项**语义上不适用**:`edge_points` 仅在 numpy 缺失时才走(numpy 在场时用 `edge_array` 返回的 ndarray),无 numpy 无从建 ndarray。剩余纯 Python 分支(`edge_mask` 的 bytearray 逐值、`line_candidates` 垂直 counts 逐像素)**刻意保留为参考实现**:它只在 `PPT_REBUILD_MEASUREMENT_ENGINE=python` 或无 numpy 时执行,正是引擎一致性测试要对照的路径;强行改 numpy 会让「python 引擎」名不副实。故不改。

- 定位: `calibrate:72-90 edge_points`(逐像素 `pixels[x,y]` set 推导);`extract_reference_measurements.py:199-207 edge_mask` 纯 Python 分支;`extract:340-355 line_candidates` 垂直 counts。
- 改动:
  - `edge_points` → 返回 `np.ndarray` 布尔图(替代坐标 set),下游 `crop_points`/匹配改数组切片。与 P0-1 一起改。
  - `edge_mask` 纯 Python `bytearray(... for value in raw)` → `(np.frombuffer(raw,uint8) >= threshold)`。
  - 垂直 counts 用 `array.sum(axis=0)`。
- 验收: `test_extract_reference_measurements.py::test_accelerated_and_python_engines_keep_geometry_compatible` 仍通过(几何一致)。

## P0-3 并行化 extract 逐页循环 ☑

> 完成(2026-07-05):新增 `--jobs`(默认 0 → `min(cpu_count, 页数)`;`--jobs 1` 强制串行调试)。`worker_count==1` 走原串行分支(逐字节等价);否则 `ProcessPoolExecutor` + `as_completed`,按 page index 回填 `results_by_index` 并 `sorted` 重组,`failed_pages` 按 page 排序 → 与串行**逐字节一致**。`analyze_image` 是模块级纯函数、参数(Path/int/str)全可 pickle;各 worker 按 `path.stem` 写各自注释图无冲突。新增回归 `test_parallel_output_is_byte_identical_to_serial`(`--jobs 1` vs `--jobs 3`,共享 `--annotated-dir` 使路径字段一致)。Windows spawn 实测正常,42 测试全绿。

- 定位: `extract:834-853` 主循环。
- 改动: `concurrent.futures.ProcessPoolExecutor`,`--jobs N`(默认 `min(os.cpu_count(), len(files))`);按 index 回填保持页序;`failedPages` 聚合不变;单进程(`--jobs 1`)时保持现行为(便于调试)。
- 注意: `analyze_image` 需可 pickle(纯函数,已 OK);注释图路径按 `path.stem`,无冲突。
- 验收: 输出 JSON 与串行逐字节一致(pages 顺序、failedPages)。加 `--jobs 1` 回归。

## P0-4 缩小 audit O(n²) 重叠循环(可选,低优先)☐(暂缓)

> 状态(2026-07-05):计划标注「可选,低优先」。实际每页文本框数量通常为个位到几十,O(n²) 常数极小,非瓶颈;扫描线剪枝需谨慎保持 totals 与配对顺序一致。价值有限、有改动风险,**暂缓**,待 P2/P3 主体完成后再评估。

- 定位: `audit_pptx_text_frames.py:436-437`(text×text)、`:460-461`(text×thin)。
- 改动: 按 y 排序 + 扫描线剪枝,仅对 y 区间可能重叠的对调用 `overlap()`。
- 验收: totals 与现有一致;`test_audit_pptx_text_frames.py` 全绿。

## P0-5 消除 extract counts 重复全扫描 ☐(暂缓,仅惠及 fallback)

> 状态(2026-07-05):numpy 路径的 `array.sum(axis=1)`/`sum(axis=0)` 基于 `np.frombuffer(...).reshape(...)` 的**零拷贝视图**(近乎免费),两次求和本就都需要,合并无益。真正的两遍全扫描只存在于**纯 Python 分支**(`PPT_REBUILD_MEASUREMENT_ENGINE=python`/无 numpy),合并为单遍历仅对该降级路径有约 2× 收益。收益局限、需改 `line_candidates`/`analyze_image` 签名引入风险,**暂缓**。

- 定位: `extract:335-355`,水平与垂直各做一次全 W×H 扫描(纯 Python 分支)。
- 改动: 复用同一 reshape 数组,`sum(axis=1)`/`sum(axis=0)` 各取一次;纯 Python 分支合并为单遍历同时累加双向。
- 验收: 引擎一致性测试通过。

## 基准脚本(自建,勿提交为产物脚本,放 docs 或临时目录)

用 3 张 2K 参考图 + 3 张 render,`PPT_REBUILD_MEASUREMENT_ENGINE=python`,计时 calibrate 改前/改后。
