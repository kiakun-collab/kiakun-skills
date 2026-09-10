# Visual Extraction Pass

生成 layout-spec 前建立一份有来源的对象清单，默认按 [adaptive-verification.md](adaptive-verification.md)。

1. 记录源尺寸、目标画布与唯一 coordinateTransform，非 16:9 保持比例。
2. 一次整页抽取：阅读顺序、文字表格、原生形状、图片、间距。用户已提供的文案直接绑定对象，不从图片再次识别；只读取未覆盖部分。对象记录 id、role、bbox、source/evidence、编辑策略；疑点加入 risks。
3. 来源可以是原 PPTX 对象、实际观察 bbox、可用 OCR 或测量候选。候选需校正，不能直接当作最终形状清单；无疑点无需所有候选标注图。
4. 普通单页用精简 JSON；[visual-extraction-template.json](../assets/templates/visual-extraction-template.json) 删除不适用示例，最终形状进入 shapes[]。
5. 由清单生成统一 layout-spec，引用 sourceExtractionId；公共模板/样式只记一次，逐页展开交给 [数据构建器](data-driven-build.md)。用户要求统一模板时，原图观测与目标模板参数分开保存，共同结构可引用一次模板依据，无须逐页重新测量非意图性漂移。坐标映射先建立，渲染前计算校准状态 PENDING，不要求预先 PASS。
6. 构建、渲染，再验证字形、换行、位置层级，写 renderVerification。仅风险项启动 [autonomous-calibration.md](autonomous-calibration.md)。

规则矩形、圆角、线、表格用原生对象；照片、纹理、光晕和羽化用图片。有意覆盖记录 overlapPolicy/allowedOverlays，不影响可读性不计碰撞。同句多样式文字用单文本框 runs，不用 auto-shrink 掩盖溢出。共享样式可以复用，实际页面仍逐页看最终渲染。
