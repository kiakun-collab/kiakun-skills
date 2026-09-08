# Full Layered Workflow

Mode C 在 B 基础上让约定范围内的背景、人物、内容图独立。可分层不意味着照片必须矢量化，也不意味着自动启用最重校准；只指定部分主体时不扩展为全页全部拆分。

1. 冻结来源和用户要求，优先提取已有 PPTX 的文字、素材、坐标和层级。
2. 逐对象 asset-audit 明确复用、裁切、抠图或生成，只对用户要求的范围分层。`mustRemainIndependentImages` 与 `mustHaveAlpha` 使用同一资产 ID；独立照片不必有 alpha。按 [asset-policy.md](asset-policy.md) 设置透明性失败处理。
3. 按 visual-extraction-pass 抽取坐标；复杂/批量页可运行 `extract_reference_measurements.py`，普通页记录实际 bbox 与来源。
4. 建立 `layout-spec.json`，保留 sourceExtractionId 和唯一坐标映射，共享样式可复用。计算校准在渲染后进行。
5. 制作独立资产与文字结构交错推进；每张素材返回即检查实际 alpha，按就绪页保存 PPTX 并渲染。首次透明性失败走已约定交接，不等待其余失败素材逐个重生。
6. 一次逐页检查可读性、还原度、分层；按风险启动坐标/字体校准，strict 保留完整计算证据。
7. 只修失败区域，受影响页重渲染。按 [qa-standards.md](qa-standards.md) 与 [Level 3 检查表](../assets/templates/level-3-delivery-checklist.md) 验证。

底色用 background fill，主要素材可独立移动替换。照片内部文字是否重建取决于边界。默认可交付 `MANUAL_CUTOUT_REQUIRED` 并列出待抠素材，不声明完整 Level 3；其余页面继续完成。用户明确要求全部自动完成时，透明性未解决仍是未完成项，不自动改 B。已获允许的例外记录在 asset-audit。

整页参考图不进入成品，拆层后仍保持构图、色彩和边缘过渡；“可编辑”不能解释重大视觉偏差。
