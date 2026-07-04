# P4 · 测试补强

统一放 `tests/`,沿用 unittest + subprocess 风格,复用 `tests/common.py` 造件。

## P4-1 calibrate 纯 Python 回退路径(正确性关键)☑

> 完成(2026-07-05,随 P0-1):`test_no_cv2_numpy_branch_matches_known_translation`(强制 cv2=None,走 numpy 分支)+ `test_pure_python_fallback_matches_known_translation`(强制 np=None+cv2=None,走 edge_points+match_anchor set 版),均验证 known-translation (4,3)。此前这两条路径零覆盖。

- 现状: `match_anchor`(慢路径)无测试——正确性关键路径未受保护。
- 新增: monkeypatch/env 强制 cv2=None(及可选 numpy=None),对 known-translation 图验证 dx/dy 与预期一致(±1px)。**保护 P0-1 重写,须在 P0-1 动工前先落地基线。**

## P4-2 页码提取一致性(保护 P2-1)☑

> 完成(2026-07-05,随 P2-1):`tests/test_page_number_contract.py` 断言共享 `extract_page_number` label 优先,且 calibrate 与 make_comparison 对同组文件名映射逐一相等(并断言二者引用同一函数对象)。

- 新增: 对同一组文件名,断言 calibrate 的 `page_number` 与 make_comparison 的 `extract_page_number` 产出相同映射。

## P4-3 CJK 叠加不崩(保护 P2-2)☑

> 完成(2026-07-05,随 P2-2):`tests/test_overlay_font.py` 渲染含中文的标签不抛异常、返回可用字体、Windows 上实测解析到 FreeTypeFont(msyh.ttc)而非默认 bitmap。

- 新增: 用含中文 shapeName 的测量/anchor 数据渲染注释图,断言不抛异常且加载了非默认字体(系统存在 CJK 字体时)。

## P4-4 异常语义(保护 P2-3)☑

> 完成(2026-07-05,随 P2-3):`test_all_bad_images_exit_with_code_2`(extract 全坏图→退出 2、failedPages 完整)+ `test_single_bad_item_is_recorded_without_aborting`(score 单坏 item 记 failures、好 item 仍评分、不整体中止)。

- 新增两例:
  - (a) extract 输入全为坏图 → 退出码 2 且 failedPages 完整;
  - (b) score_typography 单个 item 坏(renderCrop 越界)→ 该 item 记 failures,其余 item 正常,不整体中止。

## P4-5 group_transform 直接单测(保护 P1-1)☑

> 完成(2026-07-05):`tests/test_pptx_common.py` 直接调用共享 `group_transform`,覆盖正常嵌套组、父变换合成、rot!=0→None、缺 chOff/chExt、child extent 为 0、无 xfrm;并附带 `shape_name`(kind 与 tag 推断)与 `slide_sort_key` 单测。

- 新增: 直接调用共享 `group_transform`,覆盖: 正常嵌套组、rot!=0 返回 None、缺 chOff/chExt、child extent 为 0。脱离端到端更快更精确。

## 运行

```bash
python -m pytest tests/ -q
# 或
python -m unittest discover tests
```
