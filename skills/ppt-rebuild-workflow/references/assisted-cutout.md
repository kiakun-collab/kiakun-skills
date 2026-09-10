# 复杂背景的辅助分割

仅在用户所需独立对象嵌在混合背景中、可见轮廓比较明确且需要保留原貌时使用。适合实体人物、卡通角色、产品；不是通用半透明重建或遮挡补全。已有可用透明图直接复用；照片无需独立主体时正常裁切。

## 执行与停止

1. 查看原图和有上下文的主体局部，确定提取范围。用户把人物与手持道具当一个对象时一起提取；不要自动拆成多个对象，也不要自动删除属于对象的悬空配件。
2. 在原始图像像素坐标中记录 ROI 和粗轮廓；腿间、手臂间等孔洞标为确定背景。由模型根据实际查看的图像提供提示，不让用户逐点描边，也不把普通矩形裁切框当精确轮廓。
3. 运行脚本：粗轮廓内部提供前景种子，附近留不确定带，GrabCut 分割后做窄边缘颜色估计。默认保留所有分离组件，不按“最大连通块”删掉手指、配件等。依赖 Pillow、NumPy、OpenCV；启用边缘修正还需 SciPy，仅此路线检查依赖，不为普通页面启动安装流程。
4. 查看 `preview.png` 深浅底对照，关注细角、手指、白字、高光、腿间孔洞及背景残留。有明确问题时仅修改相应轮廓/背景提示，必要时用 `excludePolygons` 精确排除残留；不要将这次图片的坐标或“删除白色/黑色”阈值写成通用规则。
5. 默认一次初试，最多再做一轮有证据的局部修正，且服从任务剩余返修预算；达到要求即停止。依赖不可用、前景背景难分或第二次仍明显不合格时保留未完成项，执行 asset-policy 的交接/required 策略，推进无关页面。用户明确要求继续精修时才扩大预算。

脚本返回成功不等于抠图合格。通过深浅底检查后按同一资产 ID 更新现有 manifest 的 path/source，保留 cutout.json 的定位信息，运行 `assets` 检查通道，最终还要验证 PPT 中实际位置和移动后的边缘。自动报告不填写视觉 PASS。首次生成素材不透明的默认交接规则不变；本路线用于原图提取或用户要求自动抠图的适用对象。

## 调用与提示

```powershell
python scripts/extract_asset_grabcut.py --input reference.png --hints cutout-hints.json --out-dir work/cutout-v1
```

提示示例（仅展示字段，实际坐标必须来自当前源图）：

```json
{
  "sourceSize": [1280, 720],
  "roi": [900, 360, 1280, 720],
  "foregroundPolygons": [[[950, 410], [1070, 380], [1230, 470], [1220, 680], [960, 690]]],
  "backgroundPolygons": [],
  "excludePolygons": [],
  "uncertaintyRadius": 7,
  "edgeRadius": 2,
  "iterations": 5,
  "padding": 12
}
```

- 所有点均为**源图像素**，不是百分比或 ROI 内局部坐标；`sourceSize` 必须与实际图像一致。ROI 为 `[left, top, right, bottom]`，右下不包含，每个多边形至少三个不共线点且在 ROI 内。
- `foregroundPolygons` 是粗略主体区域，允许多个；`backgroundPolygons` 是确定背景/孔洞。`excludePolygons` 用于目视确认后的局部排除，最终 alpha 在这些区域固定为 0。
- 默认值如上；半径均为源像素，按当前分辨率调整。`edgeRadius=0` 可关闭颜色估计；不确定细节优先改提示，避免不断调全局阈值。
- 出图不缩放源像素，内部颜色保留；边缘 RGB 可能为去除底色污染而调整。画面已裁掉或被遮住的身体部分不会补全，也不会恢复主体后方被遮挡的背景。

## 放回 PPT 的坐标

`visibleBBoxSource` 给出真实可见主体的源图边界；PNG 外侧透明 padding 不算主体高度。默认输出按 alpha bbox 裁切并加 padding，`outputToSource.translateX/Y` 给出 PNG 左上角对应的源图坐标，可能落在源图外。

按任务已有的唯一 `sourcePxToCanvas` 映射，把 **PNG 的整个外框**映射到 PPT，不拿含 padding 的图片高度冒充主体高度。对缩放和平移映射：

```text
pptX = translateX * scaleX + offsetX
pptY = translateY * scaleY + offsetY
pptW = outputWidth  * scaleX
pptH = outputHeight * scaleY
```

这样透明留白也参与位置计算，主体仍落在原始坐标。不得因此新建另一套百分比坐标。

## 能力说明与计时

这是“模型辅助定位 + 程序分割”，包括粗轮廓提示和可选局部修正，不能称为已经验证过的全自动万能抠图。当前真实案例验证了两个人物与木牌一起提取；其他主体仍需实际边缘检查。脚本的 `processingMs` 仅为计算时间，提示制作、看图和修正耗时另外记录到现有 runner 事件，不能用毫秒级计算时间代表整项耗时。
