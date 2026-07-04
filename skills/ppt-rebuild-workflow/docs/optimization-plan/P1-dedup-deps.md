# P1 · 去重与依赖治理(铺底,最先做)

## P1-1 抽取 scripts/_pptx_common.py ☑

> 完成(2026-07-04):新建 `scripts/_pptx_common.py`,导出 `NS`、`slide_sort_key`、`group_transform`、统一版 `shape_name(shape, kind=None)`(kind=None 时按 tag 推断 cxnSp/sp,兼容 text_frames 原语义;kind="shape"/"picture" 兼容 structure)。两 audit 脚本改为 `from _pptx_common import ...`。37 测试全绿,输出逐字节一致。

- 重复源:
  - `group_transform`: `audit_pptx_text_frames.py:224-256` ≡ `audit_pptx_structure.py:105-137`(逐行相同)
  - `slide_sort_key`: `text_frames:210` / `structure:57`
  - `NS` 常量 / `shape_name` / raw-frame 提取
- 改动: 新建 `scripts/_pptx_common.py`,导出 NS、group_transform、slide_sort_key、iter_shapes 等;两 audit 脚本改为 import。
- 注意: 两脚本 `shape_name` 签名不同(text_frames 单参猜 cxnSp/sp;structure 双参 kind)。保留各自语义或提供带 kind 的统一版 + 薄封装。
- 验收: 两 audit 全部测试逐字节一致。

## P1-2 抽取 scripts/_image_common.py ☑

> 完成(2026-07-05):新建 `scripts/_image_common.py`,导出 `IMAGE_EXTENSIONS`、`natural_key`、`percentile_from_histogram`(采 extract 的规范实现;score 原 `percentile` 在 256-bin L 直方图下逐值等价,已替换)、`load_image_rgb(path)`、`edge_binary(image, use_numpy=…)`(供 P0-1/P0-2 复用;`use_numpy` 仅选快慢分支,掩码内容与原 extract `edge_mask` 逐字节一致)。extract/calibrate/score/make_comparison 均改为 import;extract `edge_mask` 变薄封装、calibrate `edge_points` 阈值改用 `max(24, percentile_from_histogram(...,0.9))`(与原内联逻辑逐值等价)。39 测试全绿(含引擎一致性 + calibrate 平移基线 PASS)。

- 重复源:
  - `natural_key`: `extract:51` / `make_comparison:18`
  - `IMAGE_EXTENSIONS`: `extract:35` / `calibrate:29` / `make_comparison:26`
  - histogram 百分位: `extract:74 percentile_from_histogram` / `calibrate:78-83` 内联 / `score_typography:18 percentile`(三套实现)
  - 边缘阈值逻辑(`extract:199-207` / `calibrate:93-101` / `score:58-59`)
- 改动: 导出 `IMAGE_EXTENSIONS`、`natural_key`、`percentile_from_histogram`、`load_image_rgb(path)`、`edge_binary(image)->np.ndarray`。
- 验收: 各脚本行为不变;引擎一致性测试通过。

## P1-3 统一 JSON 写出 + stdout 治理 ☑

> 完成(2026-07-05):新建 stdlib-only 的 `scripts/_io_common.py`(避免 audit 脚本被迫引入 PIL),导出 `write_json(path,obj)`(`ensure_ascii=False`+`indent=2`+`mkdir(parents,exist_ok)`,逐字节等价)与 `make_stdout_robust()`。6 个写 JSON 的脚本(extract/calibrate/score/text_frames/structure/validate)+ make_comparison 的 pairing 均改用 `write_json`;extract/calibrate 在 `print(output_path)` 前调用 `make_stdout_robust()`(对齐 structure:501)。新增回归 `test_cli_survives_gbk_stdout_with_non_ascii_output_path`(extract & calibrate):用非 GBK 可编码的 emoji 输出路径,在 `PYTHONIOENCODING=gbk` 下断言 rc=0 且 stderr 无 `UnicodeEncodeError`——已确认去掉 guard 会真实崩溃。共 39 测试全绿。

- 重复源: 6 脚本各有 `mkdir(parents=True); write_text(json.dumps(..., ensure_ascii=False, indent=2), encoding="utf-8")`。
- 改动: `_image_common`(或新 `_io_common`)加 `write_json(path, obj)`。
  另:`extract` / `calibrate` 的 `print(output_path)` 在 GBK 控制台打印非 ASCII 路径会抛错;统一加 `if hasattr(sys.stdout,"reconfigure"): sys.stdout.reconfigure(errors="backslashreplace")`(对齐 `structure:501`)。
- 验收: `test_audit_pptx_structure.py::test_cli_survives_gbk_stdout` 类同保护对 extract/calibrate 也成立(可加回归)。

## P1-4 依赖清单(全仓库当前缺失)☑

> 完成(2026-07-04):新建 skill 根目录 `pyproject.toml`,setuptools 后端、`requires-python>=3.9`、`dependencies=["Pillow>=9"]`、`[fast]=numpy/scipy/opencv-python-headless`、`[dev]=python-pptx`;因仓库是扁平脚本集,`[tool.setuptools] packages=[]` 只装元数据+依赖不做自动发现。`pip install -e ".[fast,dev]" --dry-run` 成功:editable 元数据生成、依赖全部解析。

- 改动: 新建 `pyproject.toml`(skill 根目录):
  - `requires-python = ">=3.9"`
  - dependencies = `["Pillow>=9"]`
  - optional `[fast]` = `["numpy>=1.23","scipy>=1.9","opencv-python-headless>=4.6"]`
  - optional `[dev]` = `["python-pptx>=0.6"]`
- 验收: `pip install -e .[fast,dev]` 成功;`pip install -e .` 后 audit_* 与纯 Python 路径可运行。
