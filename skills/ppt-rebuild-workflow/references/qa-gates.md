# QA 门禁单一事实源

> 坐标锁、视觉双门禁、禁裁剪猜字三组高重复规则的**权威定义**。其他文档如需引用这些规则，用一句话概述 + 链接本文件，避免逐字重复。

## 坐标锁（coordinate lock）

- 只用 `anchorQuality.status = PASS` 的大面板、图片区、边框和稳定长线做锚点；不用文字碎片或贯穿画布的噪声线凑数。
- 稳定宏观锚点需 3–12 个；少于 3 个时 `coordinateCalibration.status = INSUFFICIENT`，不得声明坐标校准通过。
- `coordinateCalibration.status` 只能由 `calibrate_reference_render.py` 计算（`PASS` / `INCONCLUSIVE` / `FAIL`），禁止手填 PASS。
- 所有最终对象坐标来自同一个 `coordinateTransform`；默认宏观容差 `max(6 px, 画布长边的 0.5%)`。
- 临时整页参考图只允许出现在临时校准层或 QA 产物，不得嵌入最终可编辑稿（Mode A 除外）。
- 术语区分：`anchorQuality`（extract 输出，PASS/INSUFFICIENT，指宏观锚点数量是否达标）与 `coordinateCalibration.status`（calibrate 输出，PASS/INCONCLUSIVE/FAIL，指渲染偏移是否达标）是不同对象的不同词表，勿混用。

## 视觉双门禁（visual double-gate）

两道门禁必须同时通过，缺一不可：

1. **文字可读性**：`visualOverlapCount = 0`；原生文字不被形状/连接线/图片遮挡、穿过或挤压。`graphicFrame` 与形状/图片之间的通用叠放不纳入通用碰撞门禁，只有影响文字可读性时才按此门禁处理。
2. **参考图还原度**：`visualFidelityStatus = PASS` 且 `majorFidelityDeviationCount = 0`。版式、构图、层级、色彩忠实于参考图，不要求像素级完全一致；即使不影响文字，对象的位置、尺度、裁切、前后层级或构图明显偏离参考图，仍可能构成视觉还原度偏差。

## 禁裁剪/放大猜字（no crop-to-guess）

- AI 参考图中的错字、乱码、伪字按 [text-recovery.md](text-recovery.md) 做**有来源的语义重建**（语义重建优先）；来源为原 PPTX、用户文案或可信业务资料。
- 不得通过裁剪或放大恢复文字；测量脚本产出的候选一律标为候选文字，不得写成确定文案。
